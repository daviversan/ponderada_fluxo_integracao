import os
from typing import List

import httpx

from app.schemas import CaffeineLookupResult

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/cgi/search.pl"
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

CAFFEINE_NUTRIENT_ID = 262
REQUEST_TIMEOUT = 5.0


async def search_open_food_facts(query: str) -> List[CaffeineLookupResult]:
    results: List[CaffeineLookupResult] = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            OPEN_FOOD_FACTS_URL,
            params={"search_terms": query, "json": "1", "page_size": 5},
        )
        resp.raise_for_status()
        data = resp.json()

    for product in data.get("products", []):
        name = product.get("product_name", "Unknown")
        nutriments = product.get("nutriments", {})
        caffeine_100g = nutriments.get("caffeine_100g")
        caffeine_mg = round(caffeine_100g * 10) if caffeine_100g is not None else None
        if name:
            results.append(
                CaffeineLookupResult(
                    name=name, caffeine_mg=caffeine_mg, source="Open Food Facts"
                )
            )
    return results


async def search_usda(query: str) -> List[CaffeineLookupResult]:
    results: List[CaffeineLookupResult] = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            USDA_URL,
            params={"query": query, "api_key": USDA_API_KEY, "pageSize": 5},
        )
        resp.raise_for_status()
        data = resp.json()

    for food in data.get("foods", []):
        name = food.get("description", "Unknown")
        caffeine_mg = None
        for nutrient in food.get("foodNutrients", []):
            if nutrient.get("nutrientId") == CAFFEINE_NUTRIENT_ID:
                caffeine_mg = round(nutrient.get("value", 0))
                break
        results.append(
            CaffeineLookupResult(name=name, caffeine_mg=caffeine_mg, source="USDA")
        )
    return results


async def lookup_caffeine(query: str) -> List[CaffeineLookupResult]:
    """Try Open Food Facts first, fall back to USDA on failure."""
    try:
        results = await search_open_food_facts(query)
        if results:
            return results
    except (httpx.HTTPError, Exception):
        pass

    try:
        return await search_usda(query)
    except (httpx.HTTPError, Exception):
        return []
