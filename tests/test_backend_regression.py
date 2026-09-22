import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

import backend.main as backend_main
from parse_captions import parse_caption


class BackendRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_main.app)

    def _write_products(self, file_path: Path, products: list[dict]) -> None:
        file_path.write_text(json.dumps(products), encoding="utf-8")

    def _sample_products(self) -> list[dict]:
        return [
            {
                "folder": "Cotton Kurti_20260414_024030_003",
                "price": "RM75 including postage",
                "material": "South Mix Cotton",
                "length": "6.3M",
                "care": "Dry Clean",
            },
            {
                "folder": "Silk Saree_20260414_024055_004",
                "price": "RM120",
                "material": "Silk",
                "length": "6.2M",
                "care": "Hand wash",
            },
        ]

    def test_api_search_rejects_empty_query(self):
        response = self.client.post("/api/search", json={"query": "   ", "limit": 3})
        self.assertEqual(response.status_code, 400)
        self.assertIn("must not be empty", response.json()["detail"])

    def test_webhook_rejects_unsupported_content_type(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data=json.dumps({"Body": "kurti"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 415)
        self.assertIn("Unsupported content type", response.json()["detail"])

    def test_webhook_rejects_missing_body(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data="Foo=bar",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing Body", response.json()["detail"])

    def test_search_products_returns_empty_for_blank_query(self):
        self.assertEqual(backend_main.search_products("   "), [])

    def test_search_matches_structured_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("Hand wash")
                self.assertEqual(len(results), 1)
                self.assertIn("Silk Saree", results[0]["name"])

    def test_load_products_cache_invalidates_on_file_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            initial_products = self._sample_products()
            self._write_products(products_file, initial_products)
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                first = backend_main.load_products()
                self.assertEqual(len(first), 2)

                updated_products = initial_products + [
                    {
                        "folder": "New Product_20260414_024118_005",
                        "price": "RM88",
                        "material": "Cotton",
                        "length": "5.5M",
                        "care": "Dry Clean",
                    }
                ]
                self._write_products(products_file, updated_products)
                second = backend_main.load_products()
                self.assertEqual(len(second), 3)

    def test_parse_caption_accepts_price_and_label_variants(self):
        caption = "\n".join(
            [
                "Price: Rs 499",
                "Material : Linen Cotton",
                "Length : 5.5M",
                "Care : Hand wash",
                "Kindly DM or whatsapp/telegram to +12025550123 for purchase.",
            ]
        )
        parsed = parse_caption(caption)
        self.assertEqual(parsed["price"], "Rs 499")
        self.assertEqual(parsed["material"], "Linen Cotton")
        self.assertEqual(parsed["length"], "5.5M")
        self.assertEqual(parsed["care"], "Hand wash")
        self.assertEqual(parsed["contact"], "+12025550123")

    def test_search_material_field_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("Cotton")
                self.assertEqual(len(results), 1)
                self.assertIn("Cotton Kurti", results[0]["name"])

    def test_search_folder_name_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("Silk")
                self.assertEqual(len(results), 1)
                self.assertIn("Silk Saree", results[0]["name"])

    def test_search_price_rm_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("RM75")
                self.assertEqual(len(results), 1)
                self.assertIn("RM75", results[0]["price"])

    def test_search_uppercase_query_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("HAND WASH")
                self.assertEqual(len(results), 1)

    def test_search_case_insensitive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, self._sample_products())
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("silk")
                self.assertEqual(len(results), 1)
                results_upper = backend_main.search_products("SILK")
                self.assertEqual(len(results_upper), 1)

    def test_search_returns_limit_respects_limit(self):
        products = [{"folder": f"Product_{i}", "price": f"RM{i}", "material": "Cotton", "length": "6m", "care": "Wash"} for i in range(10)]
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, products)
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("Cotton", limit=3)
                self.assertEqual(len(results), 3)

    def test_search_no_duplicates(self):
        products = [
            {"folder": "Cotton Kurti", "price": "RM50", "material": "Cotton", "length": "6m", "care": "Wash"},
            {"folder": "Cotton Kurti Blue", "price": "RM55", "material": "Cotton", "length": "6m", "care": "Wash"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            self._write_products(products_file, products)
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                results = backend_main.search_products("Cotton", limit=10)
                names = [r["name"] for r in results]
                self.assertEqual(len(names), len(set(names)))

    def test_parse_price_rm_prefix(self):
        caption = "Price: RM299\nMaterial: Cotton\nLength: 5.5m"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["price"], "RM299")

    def test_parse_price_rs_prefix(self):
        caption = "Price Rs 399\nMaterial: Silk\nLength: 6m"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["price"], "Rs 399")

    def test_parse_price_with_colon_no_space(self):
        caption = "Price:RM150\nMaterial: Cotton"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["price"], "RM150")

    def test_parse_material_with_colon(self):
        caption = "Material: 100% Cotton\nPrice: RM200"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["material"], "100% Cotton")

    def test_parse_length_saree_specific(self):
        caption = "Saree Length: 5.5m\nPrice: RM300"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["length"], "5.5m")

    def test_parse_care_washing_care(self):
        caption = "Washing Care: Hand wash only\nPrice: RM250"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["care"], "Hand wash only")

    def test_parse_care_simple(self):
        caption = "Care: Dry Clean\nPrice: RM100"
        parsed = parse_caption(caption)
        self.assertEqual(parsed["care"], "Dry Clean")

    def test_cache_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            products_file = Path(temp_dir) / "products.json"
            with patch.object(backend_main, "PRODUCTS_FILE", products_file):
                backend_main._PRODUCTS_CACHE["stamp"] = None
                backend_main._PRODUCTS_CACHE["products"] = []
                products = backend_main.load_products()
                self.assertEqual(products, [])

    def test_api_search_normalized_returns_correct_shape(self):
        response = self.client.post("/api/search", json={"query": "kurti", "limit": 2})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("count", data)
        self.assertIn("query", data)

    def test_api_search_limit_validation(self):
        response = self.client.post("/api/search", json={"query": "test", "limit": 0})
        self.assertEqual(response.status_code, 422)
        response_over = self.client.post("/api/search", json={"query": "test", "limit": 100})
        self.assertEqual(response_over.status_code, 422)

    def test_health_endpoint_returns_product_count(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("products", data)


class WebhookFormatTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_main.app)

    def test_webhook_valid_form_encoding(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data={"Body": "kurti", "From": "+12025550124"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 200)

    def test_webhook_multipart_form(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data={"Body": "saree", "From": "+12025550124"},
            headers={"Content-Type": "multipart/form-data; boundary=----boundary"},
        )
        self.assertIn(response.status_code, [200, 400])

    def test_webhook_twiml_response_format(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data={"Body": "kurti"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/xml", response.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
