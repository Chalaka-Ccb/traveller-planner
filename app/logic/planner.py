# app/logic/planner.py

from typing import List, Dict, Tuple
from app.models.itinerary import ItineraryRequest, ItineraryResponse, ItineraryDay, Place
from app.services.data_loader import get_locations, DATASET
from app.services.ors_service import _coords_row_to_latlon, optimize_route, get_leg_duration_ors
from app.logic.scoring import compute_interest_score, visit_time_hr

# Airport coordinates (Katunayake / Bandaranaike Intl Airport)
# You can override by adding a row named "Katunayake" in your CSV; this constant is fallback.

AIRPORT_NAME = "Katunayake"
AIRPORT_COORDS = (7.1806, 79.8847)  # (lat, lon)

def _find_rows_by_names(names: List[str]) -> List[Dict]:
    if not names:
        return []
    wanted = {n.strip().lower() for n in names}
    rows = DATASET.copy()
    rows["__key"] = rows["Location"].str.strip().str.lower()
    matched = rows[rows["__key"].isin(wanted)].drop(columns=["__key"])
    return matched.to_dict(orient="records")

def _candidate_pool(interests: List[str]) -> List[Dict]:
    # All locations matching interests across Sri Lanka
    return get_locations(city=None, interests=interests)

def _score_candidates(cands: List[Dict], interests: List[str]) -> List[Tuple[float, Dict]]:
    scored = []
    for row in cands:
        s = compute_interest_score(row, interests)
        scored.append((s, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def _estimate_place_cost_lkr(row: Dict, travelers: int = 1) -> float:
    fee = float(row.get("Entry_fee_LKR", 0) or 0)
    return fee * max(1, travelers)

def _pack_days_greedy(must_rows: List[Dict], optional_rows_scored: List[Tuple[float, Dict]], total_days: int, total_budget_lkr: float, travelers: int = 1, max_hours_per_day: float = 8.0):
    """
    Greedy packing similar to earlier: fill days by visit_time_hr + simple overhead.
    Returns a list of dict days (with place rows) and remaining_budget.
    """
    # Create ordered list: musts first, then optionals by score
    ordered = [ (9999.0, r) for r in must_rows ] + optional_rows_scored

    days = []
    for d in range(1, total_days + 1):
        days.append({"day": d, "rows": [], "day_total_time_hr": 0.0})

    current_day = 0
    remaining_budget = total_budget_lkr

    for score, row in ordered:
        vt = visit_time_hr(row)
        # small overhead - simplified; we will compute real travel time later
        overhead = 0.25
        need = vt + overhead
        placed = False

        # Try to put in earliest day that has capacity
        for d in range(current_day, total_days):
            if days[d]["day_total_time_hr"] + need <= max_hours_per_day:
                cost = _estimate_place_cost_lkr(row, travelers)
                if remaining_budget - cost < 0:
                    placed = False
                    break  # budget exhausted; stop trying to place
                days[d]["rows"].append(row)
                days[d]["day_total_time_hr"] += need
                remaining_budget -= cost
                placed = True
                break
            else:
                # move to next day
                current_day = d + 1
                continue

        if not placed:
            # couldn't place within day limits or budget - skip it
            continue

    return days, remaining_budget

def _get_airport_coords_from_dataset() -> Tuple[float, float]:
    # Try to find Katunayake row in dataset
    df = DATASET
    found = df[df["Location"].str.strip().str.lower() == AIRPORT_NAME.lower()]
    if not found.empty:
        r = found.iloc[0].to_dict()
        coords = _coords_row_to_latlon(r)
        if coords != (0.0, 0.0):
            return coords
    # fallback constant
    return AIRPORT_COORDS

def _reorder_and_attach_travel(days: List[Dict]) -> List[ItineraryDay]:
    """
    For each day, reorder places using optimize_route (with airport as Day1 start),
    and compute travel_time_to_next_min for each Place.
    Returns list of ItineraryDay objects.
    """
    airport_coords = _get_airport_coords_from_dataset()

    result_days: List[ItineraryDay] = []
    prev_day_last_coords = None

    for idx, d in enumerate(days):
        rows = d["rows"]
        if not rows:
            result_days.append(ItineraryDay(day=d["day"], places=[], day_total_time_hr=d["day_total_time_hr"], day_travel_time_min=0))
            continue

        # Build coords list (lat, lon) for optimizer.
        coords = []
        rows_list = []
        # If this is day 1, we'll prepend airport coords as starting point
        if idx == 0:
            coords.append(airport_coords)
            rows_list.append(None)  # placeholder for airport
        else:
            # if we have prev_day_last_coords, use it as start for today's route
            if prev_day_last_coords:
                coords.append(prev_day_last_coords)
                rows_list.append(None)

        # Add each row's coords
        for row in rows:
            rcoords = _coords_row_to_latlon(row)
            coords.append(rcoords)
            rows_list.append(row)

        # choose start_index = 0 because we prepended start coords
        start_index = 0
        order, total_seconds = optimize_route(coords, start_index=start_index)

        # Build ordered place list, skip placeholders (airport/prev day)
        ordered_places = []
        total_travel_min = 0
        for pos_i, ord_idx in enumerate(order):
            # skip any placeholder index where rows_list[index] is None
            r = rows_list[ord_idx]
            if r is None:
                continue
            # compute travel time to next (if not last real place)
            # find next real place index in order
            next_travel_min = None
            # find sequence index in order
            seq_pos = order.index(ord_idx)
            # find next ord_idx after seq_pos that corresponds to a real row
            next_min = None
            for later in order[seq_pos+1:]:
                if rows_list[later] is not None:
                    # compute leg duration from current to later
                    a = _coords_row_to_latlon(r)
                    b = _coords_row_to_latlon(rows_list[later])
                    sec = get_leg_duration_ors(a, b)
                    if sec is None:
                        # fallback using haversine estimate
                        # use haversine from ors_service
                        from app.services.ors_service import haversine_km, estimate_duration_seconds
                        dist = haversine_km(a, b)
                        sec = estimate_duration_seconds(dist)
                    next_min = int(sec // 60)
                    break
            place_model = Place(
                name=r["Location"],
                category=r.get("Nearest_City"),
                cost=float(r.get("Entry_fee_LKR", 0) or 0),
                time_required=int(visit_time_hr(r) * 60),
                description=f"{r.get('Nearest_City','')}",
                travel_time_to_next_min=next_min
            )
            ordered_places.append(place_model)
            if next_min:
                total_travel_min += next_min

        # set prev_day_last_coords for next day start (coords of last placed place)
        if ordered_places:
            last_place_row = rows_list[order[-1]]
            if last_place_row is not None:
                prev_day_last_coords = _coords_row_to_latlon(last_place_row)

        result_days.append(ItineraryDay(
            day=d["day"],
            places=ordered_places,
            day_total_time_hr=d["day_total_time_hr"],
            day_travel_time_min=total_travel_min
        ))

    return result_days

def build_itinerary(request: ItineraryRequest) -> ItineraryResponse:
    days = max(1, int(request.days))
    travelers = int(request.travelers or 1)
    total_budget = float(request.budget or 0)

    # Must visits
    must_rows = _find_rows_by_names(request.must_visit or [])

    # Candidate pool
    pool = _candidate_pool(request.interests)
    # remove duplicates already in must_rows
    must_keys = {m["Location"].strip().lower() for m in must_rows}
    pool = [p for p in pool if p["Location"].strip().lower() not in must_keys]

    # Score optionals
    scored = _score_candidates(pool, request.interests)

    # Pack days (greedy)
    days_packed, remaining_budget = _pack_days_greedy(must_rows, scored, days, total_budget, travelers)

    # Reorder each day by optimized route and attach travel times
    itinerary_days = _reorder_and_attach_travel(days_packed)


    return ItineraryResponse(
        start_from = AIRPORT_NAME,
        total_days=days,
        total_budget=total_budget,
        remaining_budget=remaining_budget,
        plan=itinerary_days
    )


