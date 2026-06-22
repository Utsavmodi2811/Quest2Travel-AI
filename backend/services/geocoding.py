"""
Dynamic Location Resolution Service.
NO hardcoded coordinates. Ever.
Flow: City Name → Nominatim → lat/lng → MongoDB cache
"""

import httpx
import hashlib
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

from database.connection import get_db
from models.travel import LocationInfo
from config.settings import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    NOMINATIM_HEADERS = {
        "User-Agent": "Quest2Travel/1.0 (contact@quest2travel.in)"
    }

    async def resolve(self, city_name: str) -> Optional[LocationInfo]:
        if not city_name or not city_name.strip():
            return None

        cache_key = "geo:" + hashlib.md5(city_name.strip().lower().encode()).hexdigest()

        # 1. Check cache
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug(f"Geocode cache hit: {city_name}")
            return cached

        # 2. Geocode
        info = await self._geocode_nominatim(city_name)

        if not info:
            logger.warning(f"Could not geocode: {city_name}")
            # Return minimal info — don't fail the whole request
            return LocationInfo(city=city_name.title(), country="India")

        # 3. Cache it
        await self._cache_result(cache_key, info)
        return info

    async def _geocode_nominatim(self, city_name: str) -> Optional[LocationInfo]:
        params = {
            "q": f"{city_name}, India",
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.API_TIMEOUT,
                headers=self.NOMINATIM_HEADERS,
            ) as client:
                resp = await client.get(
                    f"{settings.NOMINATIM_BASE_URL}/search",
                    params=params,
                )
                resp.raise_for_status()
                results = resp.json()

            if not results:
                # Try without ", India"
                params["q"] = city_name
                async with httpx.AsyncClient(
                    timeout=settings.API_TIMEOUT,
                    headers=self.NOMINATIM_HEADERS,
                ) as client:
                    resp = await client.get(
                        f"{settings.NOMINATIM_BASE_URL}/search",
                        params=params,
                    )
                    results = resp.json()

            if not results:
                return None

            r = results[0]
            addr = r.get("address", {})
            city = (
                addr.get("city") or addr.get("town") or
                addr.get("village") or addr.get("county") or
                city_name.title()
            )
            return LocationInfo(
                city=city,
                state=addr.get("state"),
                country=addr.get("country", "India"),
                latitude=float(r["lat"]),
                longitude=float(r["lon"]),
                display_name=r.get("display_name"),
            )
        except Exception as e:
            logger.error(f"Nominatim geocoding failed for '{city_name}': {e}")
            return None

    def _cache_key(self, city: str) -> str:
        return "geo:" + hashlib.md5(city.strip().lower().encode()).hexdigest()

    async def _get_cached(self, cache_key: str) -> Optional[LocationInfo]:
        try:
            db = get_db()
            doc = await db.cached_results.find_one({"cache_key": cache_key})
            if doc and doc.get("value"):
                return LocationInfo(**json.loads(doc["value"]))
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    async def _cache_result(self, cache_key: str, info: LocationInfo) -> None:
        try:
            db = get_db()
            await db.cached_results.update_one(
                {"cache_key": cache_key},
                {"$set": {
                    "cache_key": cache_key,
                    "value": info.json(),
                    "expires_at": datetime.utcnow() + timedelta(seconds=settings.GEOCODE_CACHE_TTL),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")


geocoding_service = GeocodingService()
