from __future__ import annotations

import os
import math
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps


GLOBAL_MAX_DIMENSION = 1280


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, default))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} debe estar entre {minimum} y {maximum}.")
    return value


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    value = float(os.getenv(name, default))
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} debe estar entre {minimum} y {maximum}.")
    return value


@dataclass(frozen=True)
class OptimizationConfig:
    strategy: str
    inspection_max_dimension: int
    max_crops: int
    region_margin: float
    quality_threshold: float
    supplement_threshold: float
    min_region_size: int
    denoise_enabled: bool

    @classmethod
    def from_environment(cls) -> OptimizationConfig:
        strategy = os.getenv("VISION_ANALYSIS_STRATEGY", "hybrid").strip().casefold()
        if strategy not in {"global", "regions", "hybrid"}:
            raise ValueError(
                "VISION_ANALYSIS_STRATEGY debe ser global, regions o hybrid."
            )
        denoise_setting = os.getenv("VISION_DENOISE_ENABLED", "true").strip().casefold()
        if denoise_setting not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("VISION_DENOISE_ENABLED debe ser un valor booleano.")
        return cls(
            strategy=strategy,
            inspection_max_dimension=_env_int(
                "VISION_INSPECTION_MAX_DIMENSION", 640, 256, 1280
            ),
            max_crops=_env_int("VISION_MAX_CROPS", 3, 0, 8),
            region_margin=_env_float("VISION_REGION_MARGIN", 0.18, 0.0, 0.5),
            quality_threshold=_env_float("VISION_QUALITY_THRESHOLD", 0.55, 0.0, 1.0),
            supplement_threshold=_env_float(
                "VISION_SUPPLEMENT_THRESHOLD", 0.62, 0.0, 1.0
            ),
            min_region_size=_env_int("VISION_MIN_REGION_SIZE", 96, 32, 1024),
            denoise_enabled=denoise_setting in {"true", "1", "yes"},
        )


@dataclass(frozen=True)
class Region:
    coordinates: tuple[int, int, int, int]
    image: bytes
    width: int
    height: int


@dataclass(frozen=True)
class PreparedImage:
    full_image: bytes
    full_width: int
    full_height: int
    original_width: int
    original_height: int
    inspection_width: int
    inspection_height: int
    quality_score: float
    noise_level: float
    complement_score: float
    uses_regions: bool
    regions: tuple[Region, ...]


def _resize_to_fit(image: np.ndarray, max_dimension: int) -> np.ndarray:
    height, width = image.shape[:2]
    longest_side = max(width, height)
    if longest_side <= max_dimension:
        return image
    scale = max_dimension / longest_side
    return cv2.resize(
        image,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _encode_jpeg(image: np.ndarray) -> bytes:
    output = BytesIO()
    Image.fromarray(image).save(output, format="JPEG", quality=88)
    return output.getvalue()


def _measure_quality(image: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype(np.float32)
    brightness = float(np.mean(gray_float) / 255.0)
    contrast = min(float(np.std(gray_float)) / 64.0, 1.0)
    sharpness = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 180.0, 1.0)
    exposure = max(0.0, 1.0 - abs(brightness - 0.5) / 0.5)

    median = cv2.medianBlur(gray, 3)
    residual = cv2.absdiff(gray, median)
    gradient = cv2.magnitude(
        cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3),
    )
    flat_pixels = gradient < 12
    noise_level = (
        float(np.median(residual[flat_pixels])) if np.any(flat_pixels) else 0.0
    )
    noise_quality = max(0.0, 1.0 - noise_level / 18.0)
    quality = (
        0.30 * exposure
        + 0.20 * contrast
        + 0.35 * sharpness
        + 0.15 * noise_quality
    )
    return min(max(quality, 0.0), 1.0), noise_level


def _intersection_over_union(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    if not intersection:
        return 0.0
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / (first_area + second_area - intersection)


def _candidate_boxes(
    inspection: np.ndarray,
    original_width: int,
    original_height: int,
    config: OptimizationConfig,
) -> list[tuple[int, int, int, int]]:
    height, width = inspection.shape[:2]
    gray = cv2.cvtColor(inspection, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 45, 135)
    edges = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8), iterations=1
    )
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    min_side = max(
        24,
        round(
            config.min_region_size
            * min(width / original_width, height / original_height)
        ),
    )
    image_area = width * height
    proposed: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area = box_width * box_height
        if (
            box_width < min_side
            or box_height < min_side
            or area < image_area * 0.003
            or area > image_area * 0.45
            or box_width > width * 0.9
            or box_height > height * 0.9
        ):
            continue
        proposed.append((x, y, x + box_width, y + box_height))

    scale_x = original_width / width
    scale_y = original_height / height
    mapped = [
        (
            max(0, round(box[0] * scale_x)),
            max(0, round(box[1] * scale_y)),
            min(original_width, round(box[2] * scale_x)),
            min(original_height, round(box[3] * scale_y)),
        )
        for box in proposed
    ]
    mapped.sort(
        key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True
    )

    selected: list[tuple[int, int, int, int]] = []
    for box in mapped:
        if all(_intersection_over_union(box, kept) < 0.55 for kept in selected):
            selected.append(box)
    return selected


def _make_region(
    original: np.ndarray,
    box: tuple[int, int, int, int],
    config: OptimizationConfig,
    reduce_noise: bool,
) -> Region | None:
    height, width = original.shape[:2]
    left, top, right, bottom = box
    margin_x = round((right - left) * config.region_margin)
    margin_y = round((bottom - top) * config.region_margin)
    left = max(0, left - margin_x)
    top = max(0, top - margin_y)
    right = min(width, right + margin_x)
    bottom = min(height, bottom + margin_y)
    crop = original[top:bottom, left:right]
    crop_height, crop_width = crop.shape[:2]
    if min(crop_width, crop_height) < config.min_region_size:
        return None
    crop = _resize_to_fit(crop, GLOBAL_MAX_DIMENSION)
    if reduce_noise:
        crop = _apply_gentle_denoising(crop)
    return Region(
        coordinates=(left, top, right, bottom),
        image=_encode_jpeg(crop),
        width=crop.shape[1],
        height=crop.shape[0],
    )


def _apply_gentle_denoising(image: np.ndarray) -> np.ndarray:
    filtered = cv2.bilateralFilter(image, 5, 20, 20)
    original_quality, original_noise = _measure_quality(_resize_to_fit(image, 640))
    filtered_quality, filtered_noise = _measure_quality(_resize_to_fit(filtered, 640))
    if (
        filtered_noise <= original_noise * 0.85
        and filtered_quality >= original_quality * 0.95
    ):
        return filtered
    return image


def prepare_image(
    content: bytes,
    config: OptimizationConfig | None = None,
) -> PreparedImage:
    settings = config or OptimizationConfig.from_environment()
    with Image.open(BytesIO(content)) as source:
        oriented = ImageOps.exif_transpose(source).convert("RGB")
        original = np.array(oriented, dtype=np.uint8, copy=True)

    original_height, original_width = original.shape[:2]
    inspection = _resize_to_fit(original, settings.inspection_max_dimension)
    quality_score, noise_level = _measure_quality(inspection)
    boxes = _candidate_boxes(inspection, original_width, original_height, settings)

    resolution_need = min(
        max(
            np.log2(max(original_width, original_height) / GLOBAL_MAX_DIMENSION),
            0.0,
        )
        / 2.0,
        1.0,
    )
    region_need = min(len(boxes) / 6.0, 1.0)
    quality_need = (
        max(
            0.0,
            (settings.quality_threshold - quality_score)
            / settings.quality_threshold,
        )
        if settings.quality_threshold > 0
        else 0.0
    )
    complement_score = min(
        1.0, 0.35 * resolution_need + 0.45 * region_need + 0.20 * quality_need
    )
    uses_regions = settings.strategy == "regions" or (
        settings.strategy == "hybrid"
        and complement_score >= settings.supplement_threshold
    )

    reduce_noise = settings.denoise_enabled and noise_level >= 10.0
    full_image = _resize_to_fit(original, GLOBAL_MAX_DIMENSION)
    if reduce_noise:
        full_image = _apply_gentle_denoising(full_image)
    regions: list[Region] = []
    if uses_regions and settings.max_crops:
        for box in boxes:
            region = _make_region(original, box, settings, reduce_noise)
            if region is not None:
                regions.append(region)
            if len(regions) >= settings.max_crops:
                break

    return PreparedImage(
        full_image=_encode_jpeg(full_image),
        full_width=full_image.shape[1],
        full_height=full_image.shape[0],
        original_width=original_width,
        original_height=original_height,
        inspection_width=inspection.shape[1],
        inspection_height=inspection.shape[0],
        quality_score=quality_score,
        noise_level=noise_level,
        complement_score=complement_score,
        uses_regions=uses_regions and bool(regions),
        regions=tuple(regions),
    )
