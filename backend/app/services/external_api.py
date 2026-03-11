import os
import logging
from typing import List

import httpx

from app.schemas import CaffeineLookupResult

logger = logging.getLogger(__name__)

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/cgi/search.pl"
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_FOODS_URL = "https://api.nal.usda.gov/fdc/v1/foods"
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

CAFFEINE_NUTRIENT_NUMBER = "262"
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
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        search_resp = await client.post(
            f"{USDA_SEARCH_URL}?api_key={USDA_API_KEY}",
            json={
                "query": query,
                "pageSize": 5,
                "dataType": ["Survey (FNDDS)", "SR Legacy"],
            },
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        foods = search_data.get("foods", [])
        if not foods:
            return []

        fdc_ids = [f["fdcId"] for f in foods]
        names = {f["fdcId"]: f.get("description", "Unknown") for f in foods}

        detail_resp = await client.post(
            f"{USDA_FOODS_URL}?api_key={USDA_API_KEY}",
            json={"fdcIds": fdc_ids, "nutrients": [262]},
        )
        detail_resp.raise_for_status()
        details = detail_resp.json()

    results: List[CaffeineLookupResult] = []
    for food in details:
        fdc_id = food.get("fdcId")
        name = names.get(fdc_id, food.get("description", "Unknown"))
        caffeine_mg = None
        for nutrient in food.get("foodNutrients", []):
            ndata = nutrient.get("nutrient", {})
            if ndata.get("number") == CAFFEINE_NUTRIENT_NUMBER:
                caffeine_mg = round(nutrient.get("amount", 0))
                break
        results.append(
            CaffeineLookupResult(name=name, caffeine_mg=caffeine_mg, source="USDA")
        )
    return results


async def lookup_caffeine(query: str) -> List[CaffeineLookupResult]:
    """Try Open Food Facts first, fall back to USDA on failure or empty results."""
    logger.info("Caffeine lookup for %r — trying Open Food Facts", query)
    try:
        results = await search_open_food_facts(query)
        if results:
            logger.info(
                "Open Food Facts returned %d result(s) for %r", len(results), query
            )
            return results
        logger.info("Open Food Facts returned 0 results for %r, falling back to USDA", query)
    except httpx.TimeoutException:
        logger.warning("Open Food Facts timed out (%.1fs) for %r, falling back to USDA", REQUEST_TIMEOUT, query)
    except httpx.HTTPStatusError as exc:
        logger.warning("Open Food Facts HTTP %d for %r, falling back to USDA", exc.response.status_code, query)
    except Exception as exc:
        logger.warning("Open Food Facts error for %r: %s, falling back to USDA", query, exc)

    logger.info("Trying USDA fallback for %r", query)
    try:
        results = await search_usda(query)
        logger.info("USDA returned %d result(s) for %r", len(results), query)
        return results
    except httpx.TimeoutException:
        logger.warning("USDA timed out (%.1fs) for %r", REQUEST_TIMEOUT, query)
    except httpx.HTTPStatusError as exc:
        logger.warning("USDA HTTP %d for %r", exc.response.status_code, query)
    except Exception as exc:
        logger.warning("USDA error for %r: %s", query, exc)

    logger.warning("All external sources failed for %r, returning empty", query)
    return []
