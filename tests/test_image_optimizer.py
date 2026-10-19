import unittest
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw

from image_optimizer import OptimizationConfig, prepare_image


def make_photo(width: int = 1400, height: int = 900) -> bytes:
    image = Image.new("RGB", (width, height), (238, 238, 238))
    draw = ImageDraw.Draw(image)
    for row in range(2):
        for column in range(4):
            center_x = round(width * (0.16 + column * 0.22))
            center_y = round(height * (0.30 + row * 0.38))
            radius = round(min(width, height) * 0.075)
            colors = ((208, 45, 35), (60, 145, 45), (235, 178, 35), (130, 75, 160))
            draw.ellipse(
                (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ),
                fill=colors[column],
                outline=(35, 35, 35),
                width=max(3, radius // 12),
            )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def config(strategy: str, **overrides: object) -> OptimizationConfig:
    values: dict[str, object] = {
        "strategy": strategy,
        "inspection_max_dimension": 640,
        "max_crops": 3,
        "region_margin": 0.18,
        "quality_threshold": 0.55,
        "supplement_threshold": 0.55,
        "min_region_size": 64,
        "denoise_enabled": False,
    }
    values.update(overrides)
    return OptimizationConfig(**values)  # type: ignore[arg-type]


class ImageOptimizerTests(unittest.TestCase):
    def test_global_strategy_never_generates_regions(self) -> None:
        result = prepare_image(make_photo(), config("global"))

        self.assertFalse(result.uses_regions)
        self.assertEqual(result.regions, ())
        self.assertEqual((result.full_width, result.full_height), (1280, 823))

    def test_regions_strategy_limits_crops_and_keeps_source_coordinates(self) -> None:
        result = prepare_image(
            make_photo(),
            config("regions", max_crops=2),
        )

        self.assertTrue(result.uses_regions)
        self.assertGreater(len(result.regions), 0)
        self.assertLessEqual(len(result.regions), 2)
        for region in result.regions:
            left, top, right, bottom = region.coordinates
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertLessEqual(right, result.original_width)
            self.assertLessEqual(bottom, result.original_height)
            with Image.open(BytesIO(region.image)) as crop:
                self.assertEqual(crop.size, (region.width, region.height))
                self.assertLessEqual(max(crop.size), 1280)

    def test_hybrid_selects_regions_for_high_resolution_busy_images(self) -> None:
        result = prepare_image(
            make_photo(3200, 2400),
            config("hybrid", supplement_threshold=0.55),
        )

        self.assertGreater(result.complement_score, 0.55)
        self.assertTrue(result.uses_regions)

    def test_empty_scene_never_emits_empty_crops(self) -> None:
        image = Image.new("RGB", (600, 400), (120, 120, 120))
        output = BytesIO()
        image.save(output, format="PNG")

        result = prepare_image(output.getvalue(), config("regions"))

        self.assertFalse(result.uses_regions)
        self.assertEqual(result.regions, ())

    def test_noise_alone_does_not_trigger_supplementary_regions(self) -> None:
        rng = np.random.default_rng(12)
        pixels = np.clip(
            rng.normal(128, 45, (480, 640, 3)), 0, 255
        ).astype(np.uint8)
        output = BytesIO()
        Image.fromarray(pixels).save(output, format="PNG")

        result = prepare_image(
            output.getvalue(),
            config("hybrid", denoise_enabled=False),
        )

        self.assertGreater(result.noise_level, 10)
        self.assertFalse(result.uses_regions)
        self.assertEqual(result.regions, ())


if __name__ == "__main__":
    unittest.main()
