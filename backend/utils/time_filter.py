from datetime import datetime, timedelta
from typing import List

from models.travel import FlightResult


def filter_flights_for_meeting(
    flights: List[FlightResult],
    meeting_date: str,
    meeting_time: str,
    transfer_minutes: int = 60,
) -> List[FlightResult]:
    """
    Keep only flights that can reach the meeting before it starts.

    meeting_date : YYYY-MM-DD
    meeting_time : HH:MM (24-hour format)
    transfer_minutes : Airport -> Meeting location
    """

    if not flights:
        return []

    latest_arrival = (
        datetime.strptime(
            f"{meeting_date} {meeting_time}",
            "%Y-%m-%d %H:%M",
        )
        - timedelta(minutes=transfer_minutes)
    )

    valid_flights = []

    for flight in flights:

        if not flight.segments:
            continue

        try:
            # Last segment = final arrival
            arrival_time = flight.segments[-1].arrival_time

            arrival_dt = datetime.strptime(
                f"{meeting_date} {arrival_time}",
                "%Y-%m-%d %H:%M",
            )

            if arrival_dt <= latest_arrival:
                valid_flights.append(flight)

        except Exception:
            continue

    return valid_flights