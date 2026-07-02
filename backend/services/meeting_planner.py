"""
Meeting Planner Service.
Feature 1-2: Given a meeting time/location, calculates:
  - Latest acceptable arrival time at destination
  - Required airport arrival time
  - Required departure window from origin
  - Hotel requirement
  - Return trip requirement

Time Intelligence: filters travel results to only those that satisfy
the computed time constraints (arrival_before, departure_after).
"""

import logging
import math
from typing import Optional, Tuple
from datetime import datetime, timedelta, date

from models.travel import MeetingInfo, TravelContext
from config.settings import settings

logger = logging.getLogger(__name__)


class MeetingPlannerService:

    def compute_travel_window(
        self,
        meeting: MeetingInfo,
    ) -> dict:
        """
        Core time-intelligence calculation.

        Given:
          meeting_time = "11:00"
          meeting_location = "Taj Hotel Mumbai"
          cab_buffer = 60 min (airport → hotel)
          checkin_buffer = 90 min (airport check-in)
          prep_buffer = 30 min (arrive before meeting starts)

        Returns:
          must_arrive_by:     "09:30"  (latest you can be at destination airport)
          departure_latest:   "07:30"  (latest flight departure from origin)
          flight_arrival_by:  "09:00"  (flight must land by this time)
          hotel_required:     bool
          return_departure_after: "13:00"  (earliest return flight if same-day)
        """
        if not meeting.meeting_time:
            return {}

        # Parse meeting time
        try:
            h, m = map(int, meeting.meeting_time.split(":"))
            meeting_dt = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        except Exception:
            return {}

        cab_buffer     = settings.CAB_BUFFER_MINUTES       # airport → venue
        checkin_buffer = settings.AIRPORT_CHECKIN_MINUTES  # check-in time needed
        prep_buffer    = settings.MEETING_PREP_MINUTES     # arrive before meeting

        # Must be at venue by this time
        venue_arrival = meeting_dt - timedelta(minutes=prep_buffer)

        # Must leave airport (land) by this time
        flight_arrival_by = venue_arrival - timedelta(minutes=cab_buffer)

        # Must be at ORIGIN airport by this time
        airport_arrival_origin = flight_arrival_by - timedelta(minutes=checkin_buffer)

        # Assume ~2h flight (generic domestic India, overridden by actual results)
        typical_flight_duration = timedelta(hours=2)
        departure_latest = airport_arrival_origin - typical_flight_duration

        result = {
            "meeting_time":          meeting.meeting_time,
            "venue_arrival_by":      venue_arrival.strftime("%H:%M"),
            "flight_arrival_by":     flight_arrival_by.strftime("%H:%M"),
            "airport_arrival_by":    airport_arrival_origin.strftime("%H:%M"),
            "departure_latest":      departure_latest.strftime("%H:%M"),
            "cab_buffer_minutes":    cab_buffer,
            "hotel_required":        meeting.hotel_required,
            "return_required":       meeting.return_required,
        }

        # Return trip: if meeting ends in N hours, earliest return departure
        if meeting.return_required or meeting.meeting_duration_hours:
            end_dt = meeting_dt + timedelta(hours=meeting.meeting_duration_hours)
            # Add 30 min buffer after meeting
            return_depart_after = end_dt + timedelta(minutes=30)
            result["return_departure_after"] = return_depart_after.strftime("%H:%M")
            result["meeting_end_time"] = end_dt.strftime("%H:%M")

        logger.info(
            f"Meeting planner: meeting@{meeting.meeting_time} → "
            f"depart by {result['departure_latest']}, "
            f"land by {result['flight_arrival_by']}"
        )
        return result

    def describe_timeline(self, window: dict) -> str:
        """Generate a human-readable journey timeline summary."""
        if not window:
            return ""
        lines = [
            f"📋 **Journey Timeline**",
            f"🛫 Depart origin by: **{window.get('departure_latest', 'N/A')}**",
            f"✈️  Land at destination by: **{window.get('flight_arrival_by', 'N/A')}**",
            f"🚗 Cab to venue (~{window.get('cab_buffer_minutes', 60)} min)",
            f"🏢 Arrive at meeting venue by: **{window.get('venue_arrival_by', 'N/A')}**",
            f"📅 Meeting at: **{window.get('meeting_time', 'N/A')}**",
        ]
        if window.get("meeting_end_time"):
            lines.append(f"🏁 Meeting ends: **{window.get('meeting_end_time')}**")
        if window.get("return_departure_after"):
            lines.append(f"🛬 Return flight from: **{window.get('return_departure_after')}** onwards")
        return "\n".join(lines)

    def filter_flights_by_arrival(
        self, flights: list, must_arrive_by: str
    ) -> list:
        """
        Feature 2: Time Intelligence.
        Keep only flights that arrive at destination by `must_arrive_by` (HH:MM).
        Returns all flights if constraint cannot be parsed.
        """
        if not must_arrive_by or not flights:
            return flights

        try:
            limit_h, limit_m = map(int, must_arrive_by.split(":"))
            limit_minutes = limit_h * 60 + limit_m
        except Exception:
            return flights

        filtered = []
        for f in flights:
            try:
                last_seg = f.segments[-1]
                arr_str = last_seg.arrival_time
                # Handle "2026-06-20T08:45:00" or "08:45"
                if "T" in arr_str:
                    arr_str = arr_str.split("T")[1]
                arr_h, arr_m = map(int, arr_str[:5].split(":"))
                arr_minutes = arr_h * 60 + arr_m
                if arr_minutes <= limit_minutes:
                    filtered.append(f)
            except Exception:
                filtered.append(f)  # can't parse → include

        logger.info(
            f"Time filter (arrive by {must_arrive_by}): "
            f"{len(filtered)}/{len(flights)} flights pass"
        )
        return filtered

    def filter_flights_by_departure(
        self, flights: list, must_depart_after: str
    ) -> list:
        """Filter return flights to only those departing after a given time."""
        if not must_depart_after or not flights:
            return flights

        try:
            lim_h, lim_m = map(int, must_depart_after.split(":"))
            lim_minutes = lim_h * 60 + lim_m
        except Exception:
            return flights

        filtered = []
        for f in flights:
            try:
                first_seg = f.segments[0]
                dep_str = first_seg.departure_time
                if "T" in dep_str:
                    dep_str = dep_str.split("T")[1]
                dep_h, dep_m = map(int, dep_str[:5].split(":"))
                dep_minutes = dep_h * 60 + dep_m
                if dep_minutes >= lim_minutes:
                    filtered.append(f)
            except Exception:
                filtered.append(f)
        return filtered


meeting_planner = MeetingPlannerService()
