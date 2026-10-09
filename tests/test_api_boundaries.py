"""Additional API boundary checks for the local portfolio demo.

These tests do not imply production security or performance validation.
"""
import unittest
from fastapi.testclient import TestClient
from backend.main import app


class ApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_search_rejects_limit_zero(self):
        response = self.client.post("/api/search", json={"query": "cotton", "limit": 0})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_limit_above_ten(self):
        response = self.client.post("/api/search", json={"query": "cotton", "limit": 11})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_query_longer_than_200(self):
        response = self.client.post("/api/search", json={"query": "x" * 201})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_missing_query(self):
        response = self.client.post("/api/search", json={"limit": 2})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_non_object_payload(self):
        response = self.client.post("/api/search", json=["cotton"])
        self.assertEqual(response.status_code, 422)

    def test_search_no_match_contract(self):
        response = self.client.post("/api/search", json={"query": "unlikely-product-name-xyz"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_webhook_rejects_blank_body(self):
        response = self.client.post(
            "/api/whatsapp/webhook",
            data={"Body": "   "},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
