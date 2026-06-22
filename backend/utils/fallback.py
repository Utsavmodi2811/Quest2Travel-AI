"""
API Fallback System.
Retries with exponential backoff (respecting 429 Retry-After when present),
then returns realistic mock data. Never crashes. Never exposes stack traces.
"""

import asyncio
import logging
import functools
from typing import Callable
from datetime import datetime

import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

MOCK_DISCLAIMER = "Live provider unavailable. Showing sample results."


def with_fallback(mock_fn: Callable):
    """
    Decorator: retries API call N times, then calls mock_fn with same args.
    mock_fn receives (origin, destination, ...) positional args — no 'self'.

    Handles 429 (rate limit), 500/502/504 (server errors), and network
    timeouts uniformly via exponential backoff. For 429 specifically, honors
    a Retry-After header if the upstream API provides one.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(self_or_first, *args, **kwargs):
            last_exc = None
            for attempt in range(settings.API_RETRY_COUNT):
                try:
                    result = await fn(self_or_first, *args, **kwargs)
                    if result is not None:
                        return result
                except httpx.HTTPStatusError as e:
                    last_exc = e
                    status = e.response.status_code if e.response is not None else "?"
                    wait = settings.API_RETRY_DELAY * (2 ** attempt)

                    if status == 429:
                        retry_after = None
                        if e.response is not None:
                            retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait = max(wait, float(retry_after))
                            except ValueError:
                                pass
                        logger.warning(
                            f"{fn.__name__} hit 429 rate limit (attempt {attempt+1}/"
                            f"{settings.API_RETRY_COUNT}). Waiting {wait}s..."
                        )
                    else:
                        logger.warning(
                            f"{fn.__name__} got HTTP {status} (attempt {attempt+1}/"
                            f"{settings.API_RETRY_COUNT}). Retrying in {wait}s..."
                        )

                    if attempt < settings.API_RETRY_COUNT - 1:
                        await asyncio.sleep(wait)
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    last_exc = e
                    wait = settings.API_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"{fn.__name__} network error (attempt {attempt+1}/"
                        f"{settings.API_RETRY_COUNT}): {type(e).__name__}. "
                        f"Retrying in {wait}s..."
                    )
                    if attempt < settings.API_RETRY_COUNT - 1:
                        await asyncio.sleep(wait)
                except Exception as e:
                    last_exc = e
                    wait = settings.API_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"{fn.__name__} attempt {attempt+1}/{settings.API_RETRY_COUNT} "
                        f"failed: {type(e).__name__}: {e}. Retrying in {wait}s..."
                    )
                    if attempt < settings.API_RETRY_COUNT - 1:
                        await asyncio.sleep(wait)

            logger.warning(
                f"{fn.__name__} exhausted retries. "
                f"Falling back to mock data. Last error: {type(last_exc).__name__ if last_exc else 'unknown'}: {last_exc}"
            )
            # Call mock with just the positional args (skip self)
            return mock_fn(*args, **kwargs)

        return wrapper
    return decorator


# ── Mock Data Generators ──────────────────────────────────────────────────────

def mock_flights(origin: str, destination: str, travel_date: str = None,
                 return_date=None, passengers: int = 1,
                 cabin_class: str = "economy", **kwargs) -> list:
    """Realistic mock flight data for any Indian city pair."""
    from models.travel import FlightResult, FlightSegment, CabinClass

    travel_date = travel_date or datetime.now().strftime("%Y-%m-%d")

    airlines = [
        ("IndiGo",    "6E", ["6E-201",  "6E-505",  "6E-7890"]),
        ("Air India", "AI", ["AI-131",  "AI-657",  "AI-805"]),
        ("SpiceJet",  "SG", ["SG-101",  "SG-233",  "SG-451"]),
        ("Vistara",   "UK", ["UK-935",  "UK-101",  "UK-213"]),
        ("IndiGo",    "6E", ["6E-333",  "6E-887",  "6E-991"]),
    ]

    dep_times = ["05:45", "07:20", "10:10", "13:30", "16:50", "19:25", "22:00"]
    durations = ["1h 50m", "2h 05m", "2h 15m", "1h 45m", "2h 30m"]

    price_map = {
        "economy":         [3299, 4499, 5199, 5899, 6799],
        "premium_economy": [8999, 10499, 11999, 13499, 15999],
        "business":        [18999, 22499, 27999, 32499, 38999],
        "first":           [52999, 64999, 78999, 89999, 99999],
    }
    prices = price_map.get(cabin_class, price_map["economy"])

    try:
        cab_enum = CabinClass(cabin_class)
    except Exception:
        cab_enum = CabinClass.ECONOMY

    results = []
    for i, (airline, code, flight_nums) in enumerate(airlines[:5]):
        dep = dep_times[i % len(dep_times)]
        dur = durations[i % len(durations)]
        # Compute arrival time simply
        dep_h, dep_m = map(int, dep.split(":"))
        dur_h = int(dur.split("h")[0])
        dur_m = int(dur.split("h")[1].strip().replace("m", ""))
        arr_h = (dep_h + dur_h + (dep_m + dur_m) // 60) % 24
        arr_m = (dep_m + dur_m) % 60
        arr = f"{arr_h:02d}:{arr_m:02d}"

        origin_code = origin[:3].upper()
        dest_code   = destination[:3].upper()

        results.append(FlightResult(
            segments=[FlightSegment(
                flight_number=flight_nums[0],
                airline=airline,
                airline_code=code,
                departure_airport=origin_code,
                departure_city=origin.title(),
                departure_time=f"{travel_date}T{dep}:00",
                arrival_airport=dest_code,
                arrival_city=destination.title(),
                arrival_time=f"{travel_date}T{arr}:00",
                duration=dur,
                aircraft="Airbus A320" if i % 2 == 0 else "Boeing 737-800",
            )],
            total_duration=dur,
            stops=0 if i < 3 else 1,
            cabin_class=cab_enum,
            price=float(prices[i]),
            currency="INR",
            baggage_allowance="Sample baggage",
            is_refundable=False,
            source="mock",
            is_mock=True,
        ))
    return results


def mock_hotels(destination: str, check_in: str = None, check_out: str = None,
                guests: int = 2, stars: int = None,
                latitude=None, longitude=None, **kwargs) -> list:
    """Realistic mock hotel data."""
    from models.travel import HotelResult

    all_hotels = [
        dict(name=f"The Taj {destination.title()}",        stars=5, score=4.9, price=12500,
             amenities=["Pool","Spa","Gym","Free WiFi","Restaurant","Bar","Butler Service"],
             dist=0.8, breakfast=True,  cancel=True),
        dict(name=f"ITC Grand {destination.title()}",      stars=5, score=4.8, price=9800,
             amenities=["Pool","Spa","Gym","Free WiFi","Restaurant","Parking"],
             dist=1.2, breakfast=True,  cancel=True),
        dict(name=f"Marriott {destination.title()}",       stars=5, score=4.7, price=8500,
             amenities=["Pool","Gym","Free WiFi","Restaurant","Business Centre"],
             dist=2.1, breakfast=False, cancel=True),
        dict(name=f"Novotel {destination.title()}",        stars=4, score=4.3, price=4200,
             amenities=["Pool","Gym","Free WiFi","Restaurant"],
             dist=3.4, breakfast=False, cancel=True),
        dict(name=f"Lemon Tree {destination.title()}",     stars=4, score=4.0, price=3100,
             amenities=["Gym","Free WiFi","Restaurant","Parking"],
             dist=4.0, breakfast=True,  cancel=False),
        dict(name=f"Ibis {destination.title()} Centre",   stars=3, score=3.8, price=1900,
             amenities=["Free WiFi","AC","24hr Desk"],
             dist=5.2, breakfast=False, cancel=True),
        dict(name=f"OYO Flagship {destination.title()}",  stars=3, score=3.4, price=1200,
             amenities=["Free WiFi","AC","TV"],
             dist=6.0, breakfast=False, cancel=False),
    ]

    results = []
    for i, h in enumerate(all_hotels):
        if stars and h["stars"] != stars:
            continue
        results.append(HotelResult(
            hotel_id=f"mock_{i}_{destination[:3].lower()}",
            name=h["name"],
            rating=h["score"],
            stars=h["stars"],
            address=f"Central Business District, {destination.title()}",
            city=destination.title(),
            price_per_night=float(h["price"]),
            currency="INR",
            amenities=h["amenities"],
            distance_from_center=h["dist"],
            review_score=h["score"],
            review_count=180 + i * 75,
            breakfast_included=h["breakfast"],
            free_cancellation=h["cancel"],
            source="mock",
            is_mock=True,
        ))

    # If star filter wiped everything, return all
    return results if results else [r for r in [
        HotelResult(
            hotel_id="mock_fallback",
            name=f"Hotel {destination.title()} Inn",
            rating=3.5, stars=stars or 3,
            address=f"{destination.title()}", city=destination.title(),
            price_per_night=2500.0, currency="INR",
            amenities=["Free WiFi","AC"],
            review_score=3.5, review_count=50,
            breakfast_included=False, free_cancellation=True,
            source="mock", is_mock=True,
        )
    ]]


from datetime import datetime


def mock_trains(origin: str, destination: str, travel_date: str = None, *args, **kwargs) -> list:
    """Realistic mock train data."""
    from models.travel import TrainResult, TrainClass_Info

    travel_date = travel_date or datetime.now().strftime("%Y-%m-%d")

    trains_data = [
        dict(
            num="12951",
            name="Mumbai Rajdhani Express",
            dep="16:55",
            arr="08:35+1",
            dur="15h 40m",
            runs=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        ),
        dict(
            num="12953",
            name="August Kranti Rajdhani",
            dep="17:40",
            arr="10:55+1",
            dur="17h 15m",
            runs=["Mon", "Wed", "Fri", "Sun"],
        ),
        dict(
            num="12009",
            name="Shatabdi Express",
            dep="06:10",
            arr="14:20",
            dur="8h 10m",
            runs=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        ),
        dict(
            num="11057",
            name="Devagiri Express",
            dep="21:05",
            arr="15:35+1",
            dur="18h 30m",
            runs=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        ),
        dict(
            num="22209",
            name="Duronto Express",
            dep="23:00",
            arr="16:45+1",
            dur="17h 45m",
            runs=["Tue", "Thu", "Sat"],
        ),
    ]

    # Station lookup table
    station_map = {
        "delhi": ("New Delhi", "NDLS"),
        "mumbai": ("Mumbai Central", "BCT"),
        "ahmedabad": ("Ahmedabad Junction", "ADI"),
        "bangalore": ("KSR Bengaluru", "SBC"),
        "pune": ("Pune Junction", "PUNE"),
        "surat": ("Surat", "ST"),
        "rajkot": ("Rajkot Junction", "RJT"),
        "chennai": ("Chennai Central", "MAS"),
        "hyderabad": ("Hyderabad Deccan", "HYB"),
    }

    origin_name, origin_code = station_map.get(
        origin.lower(),
        (origin.title(), origin[:3].upper())
    )

    dest_name, dest_code = station_map.get(
        destination.lower(),
        (destination.title(), destination[:3].upper())
    )

    results = []

    for t in trains_data:
        results.append(
            TrainResult(
                train_number=t["num"],
                train_name=t["name"],

                origin_station=origin_name,
                origin_code=origin_code,

                destination_station=dest_name,
                destination_code=dest_code,

                departure_time=t["dep"],
                arrival_time=t["arr"],
                duration=t["dur"],
                travel_date=travel_date,

                classes=[
                    TrainClass_Info(
                        class_code="SL",
                        class_name="Sleeper",
                        available_seats=52,
                        price=480,
                        quota="GENERAL",
                    ),
                    TrainClass_Info(
                        class_code="3A",
                        class_name="3rd AC",
                        available_seats=18,
                        price=1285,
                        quota="GENERAL",
                    ),
                    TrainClass_Info(
                        class_code="2A",
                        class_name="2nd AC",
                        available_seats=9,
                        price=1840,
                        quota="GENERAL",
                    ),
                    TrainClass_Info(
                        class_code="1A",
                        class_name="1st AC",
                        available_seats=4,
                        price=3155,
                        quota="GENERAL",
                    ),
                    TrainClass_Info(
                        class_code="CC",
                        class_name="Chair Car",
                        available_seats=30,
                        price=680,
                        quota="GENERAL",
                    ),
                ],

                runs_on=t["runs"],
                source="mock",
                is_mock=True,
            )
        )

    return results

def mock_buses(origin: str, destination: str, travel_date: str = None, **kwargs) -> list:
    """Realistic mock bus data."""
    from models.travel import BusResult

    buses_data = [
        dict(op="VRL Travels",      type="Volvo AC Sleeper",    price=950,  dep="21:00", arr="05:30", dur="8h 30m",
             seats=14, amenities=["USB Charging","Water Bottle","Blanket","Reading Light"]),
        dict(op="SRS Travels",      type="AC Semi-Sleeper",     price=720,  dep="22:00", arr="06:00", dur="8h 00m",
             seats=22, amenities=["USB Charging","Water Bottle","Blanket"]),
        dict(op="Orange Travels",   type="Non-AC Sleeper",      price=480,  dep="20:00", arr="05:00", dur="9h 00m",
             seats=30, amenities=["Water Bottle"]),
        dict(op="KSRTC Airavat",    type="Volvo Multi-Axle AC", price=880,  dep="22:30", arr="06:30", dur="8h 00m",
             seats=8,  amenities=["USB Charging","WiFi","Water Bottle","Blanket"]),
        dict(op="Neeta Travels",    type="AC Sleeper (2+1)",    price=1100, dep="23:00", arr="07:00", dur="8h 00m",
             seats=6,  amenities=["USB Charging","Water Bottle","Blanket","Pillow","Snacks"]),
    ]

    return [
        BusResult(
            operator=b["op"],
            bus_type=b["type"],
            departure_city=origin.title(),
            arrival_city=destination.title(),
            departure_time=b["dep"],
            arrival_time=b["arr"],
            duration=b["dur"],
            available_seats=b["seats"],
            price=float(b["price"]),
            currency="INR",
            amenities=b["amenities"],
            cancellation_policy="Free cancellation up to 2 hours before departure",
            source="mock",
            is_mock=True,
        )
        for b in buses_data
    ]


def mock_cars(location: str, pickup_date: str = None,
              return_date=None, latitude=None, longitude=None, **kwargs) -> list:
    """Realistic mock car rental data."""
    from models.travel import CarResult

    cars_data = [
        dict(name="Maruti Swift Dzire",     type="sedan",    vendor="Zoomcar",  fuel="Petrol", seats=4, trans="manual",    price=1199, features=["AC","Music System","GPS"]),
        dict(name="Hyundai Creta",          type="suv",      vendor="Revv",     fuel="Diesel", seats=5, trans="manual",    price=1899, features=["AC","GPS","Sunroof","Music System"]),
        dict(name="Honda City Automatic",   type="sedan",    vendor="Zoomcar",  fuel="Petrol", seats=4, trans="automatic", price=1599, features=["AC","Music System","GPS","Bluetooth"]),
        dict(name="Toyota Innova Crysta",   type="suv",      vendor="Myles",    fuel="Diesel", seats=7, trans="manual",    price=2499, features=["AC","GPS","Entertainment System"]),
        dict(name="Mercedes C-Class",       type="luxury",   vendor="Avis",     fuel="Petrol", seats=4, trans="automatic", price=5999, features=["AC","Leather Seats","GPS","Sunroof","Premium Audio"]),
        dict(name="Maruti Alto K10",        type="hatchback",vendor="Zoomcar",  fuel="Petrol", seats=4, trans="manual",    price=799,  features=["AC","Music System"]),
    ]

    return [
        CarResult(
            vehicle_name=c["name"],
            vehicle_type=c["type"],
            vendor=c["vendor"],
            fuel_type=c["fuel"],
            seats=c["seats"],
            transmission=c["trans"],
            pickup_location=location.title(),
            price_per_day=float(c["price"]),
            currency="INR",
            features=c["features"],
            source="mock",
            is_mock=True,
        )
        for c in cars_data
    ]
