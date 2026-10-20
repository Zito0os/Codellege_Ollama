import os
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from image_optimizer import OptimizationConfig, prepare_image
from tests.test_image_optimizer import make_photo
from api import app
from api import extraer_alimentos, formatear_resultado


def ollama_response(content: str, done_reason: str = "stop") -> SimpleNamespace:
    return SimpleNamespace(
        message=SimpleNamespace(
            content=json.dumps(
                {"alimentos": [item.strip() for item in content.split(",")]},
                ensure_ascii=False,
            )
        ),
        done=True,
        done_reason=done_reason,
    )


class VisionApiTests(unittest.TestCase):
    def test_english_model_names_are_normalized_and_deduplicated(self) -> None:
        foods = extraer_alimentos(
            "avocado, avocados, milk, eggs, blueberries, broccoli, mushrooms, "
            "chicken, tomatoes, carrots, green grapes, cauliflower, cauliflor, corn, "
            "ham, peaches, orange juice, marmelada, scallions"
        )

        self.assertEqual(
            foods,
            [
                "aguacate",
                "leche",
                "huevo",
                "arandano",
                "brocoli",
                "champinon",
                "pollo",
                "tomate",
                "zanahoria",
                "uva",
                "coliflor",
                "maiz",
                "jamon",
                "durazno",
                "jugo de naranja",
                "mermelada",
                "cebollin",
            ],
        )
        formatted = formatear_resultado(foods)
        self.assertIn("- arándano", formatted)
        self.assertIn("- maíz", formatted)
        self.assertIn("- jamón", formatted)

    def test_global_endpoint_keeps_response_shape_and_uses_one_call(self) -> None:
        client = TestClient(app)
        with (
            patch.dict(os.environ, {"VISION_ANALYSIS_STRATEGY": "global"}),
            patch("api.ollama.chat", return_value=ollama_response("tomate, lechuga")) as chat,
        ):
            response = client.post(
                "/analizar",
                files={"imagen": ("fridge.png", make_photo(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"resultado"})
        self.assertIn("tomate", response.json()["resultado"])
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(chat.call_args.kwargs["format"]["properties"]["alimentos"]["maxItems"], 20)
        self.assertEqual(chat.call_args.kwargs["options"]["num_predict"], 192)

    def test_regions_add_only_bounded_calls_and_merge_duplicate_names(self) -> None:
        image_config = OptimizationConfig(
            strategy="regions",
            inspection_max_dimension=640,
            max_crops=2,
            region_margin=0.18,
            quality_threshold=0.55,
            supplement_threshold=0.62,
            min_region_size=64,
            region_fallback_edge_threshold=0.06,
            denoise_enabled=False,
        )
        prepared = prepare_image(make_photo(), image_config)
        responses = [ollama_response("tomate, manzana")] + [
            ollama_response("tomate, pera")
        ] * len(prepared.regions)
        client = TestClient(app)
        with (
            patch.dict(os.environ, {"VISION_ANALYSIS_STRATEGY": "regions"}),
            patch("api.prepare_image", return_value=prepared),
            patch("api.ollama.chat", side_effect=responses) as chat,
        ):
            response = client.post(
                "/analizar",
                files={"imagen": ("fridge.png", make_photo(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(chat.call_count, 1 + len(prepared.regions))
        self.assertLessEqual(chat.call_count, 3)
        result = response.json()["resultado"]
        self.assertIn("tomate", result)
        self.assertIn("manzana", result)
        self.assertIn("pera", result)
        self.assertEqual(result.count("- tomate"), 1)
        self.assertTrue(
            all(
                "recorte de detalle" in call.kwargs["messages"][0]["content"]
                for call in chat.call_args_list[1:]
            )
        )
        self.assertTrue(
            all(
                "tomate, manzana" not in call.kwargs["messages"][0]["content"]
                for call in chat.call_args_list[1:]
            )
        )

    def test_stream_endpoint_keeps_ndjson_events_and_global_call_count(self) -> None:
        client = TestClient(app)
        with (
            patch.dict(os.environ, {"VISION_ANALYSIS_STRATEGY": "global"}),
            patch("api.ollama.chat", return_value=ollama_response("tomate")) as chat,
        ):
            response = client.post(
                "/analizar/stream",
                files={"imagen": ("fridge.png", make_photo(), "image/png")},
            )

        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(response.status_code, 200)
        self.assertEqual([event["type"] for event in events][-2:], ["token", "done"])
        self.assertEqual(chat.call_count, 1)

    def test_complete_json_is_kept_when_generation_limit_is_reached(self) -> None:
        client = TestClient(app)
        with (
            patch.dict(os.environ, {"VISION_ANALYSIS_STRATEGY": "global"}),
            patch(
                "api.ollama.chat",
                return_value=ollama_response("tomate", done_reason="length"),
            ) as chat,
        ):
            response = client.post(
                "/analizar",
                files={"imagen": ("fridge.png", make_photo(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("tomate", response.json()["resultado"])
        self.assertEqual(chat.call_count, 1)


if __name__ == "__main__":
    unittest.main()
