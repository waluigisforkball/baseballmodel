"""
inspect_pitcher.py — THROWAWAY DIAGNOSTIC. Safe to delete after we read the output.

Purpose: confirm the "robbed pitcher" case exists in the MLB feed and see how
often a pitch was RULED A BALL, challenged, and OVERTURNED TO A STRIKE — plus
how close to dead-center those pitches were.

This does NOT post anything and does NOT touch fetch.py / graphic.py / main.py.
It reuses the same feed structure the working bot already relies on, but flips
the filter to the strike direction and measures distance from the center of the
zone instead of distance outside it.

Run it over a date range and paste the output back.

  python inspect_pitcher.py --start 2026-03-27 --end 2026-05-25

(Defaults to a 7-day window ending yesterday if you give no dates.)
"""

from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import sys
import urllib.request

SCHED = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
FEED = "https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live"

PLATE_HALF_WIDTH_FT = (17.0 / 2.0) / 12.0   # 8.5 inches in feet
FT_TO_IN = 12.0
ABS_REVIEW_TYPE = "MJ"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _game_pks(date):
    sched = _get(SCHED.format(date=date))
    pks = []
    for d in sched.get("dates", []):
        for g in d.get("games", []):
            pks.append(g["gamePk"])
    return pks


def _center_distance_inches(pX, pZ, top, bot):
    """Straight-line distance (inches) from the pitch to dead-center of the zone.
    Center is pX=0 horizontally, (top+bot)/2 vertically. Smaller = more middle-
    middle = more embarrassing if it was called a ball."""
    cz = (top + bot) / 2.0
    dx_in = (pX - 0.0) * FT_TO_IN
    dz_in = (pZ - cz) * FT_TO_IN
    return math.hypot(dx_in, dz_in)


def _inside_zone(pX, pZ, top, bot):
    """Was the pitch actually inside the rulebook zone? (sanity check — a real
    'robbed pitcher' call should be a pitch that WAS in the zone.)"""
    hw = PLATE_HALF_WIDTH_FT
    return (-hw <= pX <= hw) and (bot <= pZ <= top)


def scan_game(pk):
    try:
        feed = _get(FEED.format(pk=pk))
    except Exception as e:
        print(f"[scan] feed error for {pk}: {e}", file=sys.stderr)
        return []

    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    found = []
    for play in plays:
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        for ev in play.get("playEvents", []):
            if not ev.get("isPitch"):
                continue
            details = ev.get("details", {})
            if not details.get("hasReview"):
                continue
            rev = ev.get("reviewDetails", {})
            if not rev or rev.get("reviewType") != ABS_REVIEW_TYPE:
                continue
            if not rev.get("isOverturned"):
                continue

            call = details.get("call", {})
            code = str(call.get("code", "")).upper().lstrip("*")
            # ROBBED PITCHER = current (post-overturn) call is a STRIKE.
            # Called strikes use 'C'; swinging is 'S' but that's not a take, so
            # we want 'C' (called strike). Capture both and label, to be safe.
            if not (code.startswith("C") or code.startswith("S")):
                continue

            pdat = ev.get("pitchData", {})
            coords = pdat.get("coordinates", {})
            pX = coords.get("pX"); pZ = coords.get("pZ")
            top = pdat.get("strikeZoneTop"); bot = pdat.get("strikeZoneBottom")
            if None in (pX, pZ, top, bot):
                continue

            cdist = _center_distance_inches(pX, pZ, top, bot)
            found.append(dict(
                code=code,
                desc=str(call.get("description", "")),
                center_in=round(cdist, 2),
                inside=_inside_zone(pX, pZ, top, bot),
                pitcher=matchup.get("pitcher", {}).get("fullName", "?"),
                batter=matchup.get("batter", {}).get("fullName", "?"),
                inning=about.get("inning", "?"),
                half=about.get("halfInning", "?"),
            ))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start")
    ap.add_argument("--end")
    args = ap.parse_args()

    end = (dt.date.fromisoformat(args.end) if args.end
           else dt.date.today() - dt.timedelta(days=1))
    start = (dt.date.fromisoformat(args.start) if args.start
             else end - dt.timedelta(days=6))

    all_found = []
    day = start
    while day <= end:
        pks = _game_pks(day.isoformat())
        print(f"[scan] {day} -> {len(pks)} games", file=sys.stderr)
        for pk in pks:
            for f in scan_game(pk):
                f["date"] = day.isoformat()
                all_found.append(f)
        day += dt.timedelta(days=1)

    print(f"\n=== {len(all_found)} ball->strike overturns in {start}..{end} ===")
    # sort by closest-to-center first (the most embarrassing)
    for f in sorted(all_found, key=lambda x: x["center_in"]):
        tag = "IN-ZONE" if f["inside"] else "edge/out"
        print(f'  {f["center_in"]:5.2f}" from center  [{tag}]  code={f["code"]}  '
              f'{f["pitcher"]} -> {f["batter"]}  ({f["half"]} {f["inning"]})  '
              f'{f["date"]}')

    # quick histogram of how many clear common thresholds
    print("\n=== how many within N inches of center ===")
    for thresh in (2, 3, 4, 5, 6):
        n = sum(1 for f in all_found if f["center_in"] <= thresh)
        print(f"  within {thresh}\": {n}")


if __name__ == "__main__":
    main()
