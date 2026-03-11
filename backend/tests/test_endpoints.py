from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import CaffeineLookupResult


PRODUCTS_URL = "/api/v1/products"


def _product_payload(**overrides) -> dict:
    defaults = {
        "name": "Test Coffee",
        "price_cents": 500,
        "caffeine_mg": 100,
        "currency": "USD",
    }
    defaults.update(overrides)
    return defaults


class TestCreateProductEndpoint:
    def test_create_returns_201(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload())

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Test Coffee"
        assert body["price_cents"] == 500
        assert body["caffeine_mg"] == 100
        assert body["currency"] == "USD"
        assert "id" in body

    def test_create_computes_ratio(self, client):
        resp = client.post(
            PRODUCTS_URL,
            json=_product_payload(caffeine_mg=200, price_cents=400),
        )

        assert resp.status_code == 201
        assert resp.json()["caffeine_currency_ratio"] == pytest.approx(50.0)

    def test_create_rejects_missing_name(self, client):
        payload = _product_payload()
        del payload["name"]
        resp = client.post(PRODUCTS_URL, json=payload)
        assert resp.status_code == 422

    def test_create_rejects_zero_price(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload(price_cents=0))
        assert resp.status_code == 422

    def test_create_rejects_negative_price(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload(price_cents=-100))
        assert resp.status_code == 422

    def test_create_rejects_negative_caffeine(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload(caffeine_mg=-1))
        assert resp.status_code == 422

    def test_create_rejects_invalid_currency(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload(currency="EUR"))
        assert resp.status_code == 422

    def test_create_with_brl_currency(self, client):
        resp = client.post(PRODUCTS_URL, json=_product_payload(currency="BRL"))

        assert resp.status_code == 201
        assert resp.json()["currency"] == "BRL"


class TestGetProductEndpoint:
    def test_get_existing_product(self, client):
        create_resp = client.post(PRODUCTS_URL, json=_product_payload(name="Espresso"))
        product_id = create_resp.json()["id"]

        resp = client.get(f"{PRODUCTS_URL}/{product_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Espresso"
        assert resp.json()["id"] == product_id

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get(f"{PRODUCTS_URL}/does-not-exist")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"


class TestListProductsEndpoint:
    def test_list_empty(self, client):
        resp = client.get(PRODUCTS_URL)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_all(self, client):
        client.post(PRODUCTS_URL, json=_product_payload(name="A"))
        client.post(PRODUCTS_URL, json=_product_payload(name="B"))

        resp = client.get(PRODUCTS_URL)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestUpdateProductEndpoint:
    def test_update_name(self, client):
        create_resp = client.post(PRODUCTS_URL, json=_product_payload(name="Old"))
        product_id = create_resp.json()["id"]

        resp = client.put(f"{PRODUCTS_URL}/{product_id}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["price_cents"] == 500  # unchanged

    def test_update_price_recalculates_ratio(self, client):
        create_resp = client.post(
            PRODUCTS_URL,
            json=_product_payload(caffeine_mg=100, price_cents=500),
        )
        product_id = create_resp.json()["id"]

        resp = client.put(
            f"{PRODUCTS_URL}/{product_id}", json={"price_cents": 1000}
        )
        assert resp.status_code == 200
        # 100 / 10.0 = 10.0
        assert resp.json()["caffeine_currency_ratio"] == pytest.approx(10.0)

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put(
            f"{PRODUCTS_URL}/does-not-exist", json={"name": "X"}
        )
        assert resp.status_code == 404


class TestDeleteProductEndpoint:
    def test_delete_existing_returns_204(self, client):
        create_resp = client.post(PRODUCTS_URL, json=_product_payload())
        product_id = create_resp.json()["id"]

        resp = client.delete(f"{PRODUCTS_URL}/{product_id}")
        assert resp.status_code == 204

    def test_delete_removes_product(self, client):
        create_resp = client.post(PRODUCTS_URL, json=_product_payload())
        product_id = create_resp.json()["id"]

        client.delete(f"{PRODUCTS_URL}/{product_id}")

        resp = client.get(f"{PRODUCTS_URL}/{product_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete(f"{PRODUCTS_URL}/does-not-exist")
        assert resp.status_code == 404


class TestSearchProductsEndpoint:
    def test_search_filters_by_name(self, client):
        client.post(PRODUCTS_URL, json=_product_payload(name="Red Bull"))
        client.post(PRODUCTS_URL, json=_product_payload(name="Monster Energy"))
        client.post(PRODUCTS_URL, json=_product_payload(name="Red Eye Coffee"))

        resp = client.get(f"{PRODUCTS_URL}/search", params={"q": "red"})
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()}
        assert names == {"Red Bull", "Red Eye Coffee"}

    def test_search_returns_empty_for_no_match(self, client):
        client.post(PRODUCTS_URL, json=_product_payload(name="Espresso"))

        resp = client.get(f"{PRODUCTS_URL}/search", params={"q": "matcha"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_requires_query_param(self, client):
        resp = client.get(f"{PRODUCTS_URL}/search")
        assert resp.status_code == 422


class TestRankedProductsEndpoint:
    def test_ranked_returns_sorted_by_ratio_desc(self, client):
        client.post(
            PRODUCTS_URL,
            json=_product_payload(name="Low", caffeine_mg=10, price_cents=1000),
        )  # ratio = 1.0
        client.post(
            PRODUCTS_URL,
            json=_product_payload(name="High", caffeine_mg=300, price_cents=100),
        )  # ratio = 300.0
        client.post(
            PRODUCTS_URL,
            json=_product_payload(name="Mid", caffeine_mg=100, price_cents=200),
        )  # ratio = 50.0

        resp = client.get(f"{PRODUCTS_URL}/ranked")
        assert resp.status_code == 200
        products = resp.json()
        assert len(products) == 3
        assert products[0]["name"] == "High"
        assert products[1]["name"] == "Mid"
        assert products[2]["name"] == "Low"

    def test_ranked_empty(self, client):
        resp = client.get(f"{PRODUCTS_URL}/ranked")
        assert resp.status_code == 200
        assert resp.json() == []


class TestLookupCaffeineEndpoint:
    @patch("app.routers.products.lookup_caffeine", new_callable=AsyncMock)
    def test_lookup_returns_results(self, mock_lookup, client):
        mock_lookup.return_value = [
            CaffeineLookupResult(
                name="Generic Coffee", caffeine_mg=95, source="Open Food Facts"
            )
        ]

        resp = client.get(f"{PRODUCTS_URL}/lookup", params={"q": "coffee"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["name"] == "Generic Coffee"
        assert results[0]["caffeine_mg"] == 95
        assert results[0]["source"] == "Open Food Facts"
        mock_lookup.assert_called_once_with("coffee")

    @patch("app.routers.products.lookup_caffeine", new_callable=AsyncMock)
    def test_lookup_returns_empty_on_no_results(self, mock_lookup, client):
        mock_lookup.return_value = []

        resp = client.get(f"{PRODUCTS_URL}/lookup", params={"q": "xyznonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("app.routers.products.lookup_caffeine", new_callable=AsyncMock)
    def test_lookup_returns_usda_fallback(self, mock_lookup, client):
        mock_lookup.return_value = [
            CaffeineLookupResult(
                name="Brewed Coffee", caffeine_mg=63, source="USDA"
            )
        ]

        resp = client.get(f"{PRODUCTS_URL}/lookup", params={"q": "brewed coffee"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["source"] == "USDA"

    def test_lookup_requires_query_param(self, client):
        resp = client.get(f"{PRODUCTS_URL}/lookup")
        assert resp.status_code == 422

    @patch("app.routers.products.lookup_caffeine", new_callable=AsyncMock)
    def test_lookup_returns_multiple_results(self, mock_lookup, client):
        mock_lookup.return_value = [
            CaffeineLookupResult(name="Espresso", caffeine_mg=212, source="Open Food Facts"),
            CaffeineLookupResult(name="Drip Coffee", caffeine_mg=95, source="Open Food Facts"),
            CaffeineLookupResult(name="Decaf", caffeine_mg=3, source="Open Food Facts"),
        ]

        resp = client.get(f"{PRODUCTS_URL}/lookup", params={"q": "coffee"})
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    @patch("app.routers.products.lookup_caffeine", new_callable=AsyncMock)
    def test_lookup_handles_null_caffeine(self, mock_lookup, client):
        mock_lookup.return_value = [
            CaffeineLookupResult(name="Unknown Drink", caffeine_mg=None, source="Open Food Facts"),
        ]

        resp = client.get(f"{PRODUCTS_URL}/lookup", params={"q": "unknown"})
        assert resp.status_code == 200
        results = resp.json()
        assert results[0]["caffeine_mg"] is None
