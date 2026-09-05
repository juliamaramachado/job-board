#!/usr/bin/env python3
"""
Animal Behavior Jobs — scraper

Pulls current job/postdoc/grad-position listings related to animal behavior,
cognition, comparative cognition, and animal welfare from a small set of
legitimate public sources, and writes them to docs/data.json for the website
to display.

Sources:
  1. USAJOBS API        — official U.S. federal government jobs API (needs a free key)
  2. Animal Behavior Society — "Positions & News" page (public, no login required)
  3. ISAE (Applied Ethology) — "Employment and Education" page (public, no login required)

Design notes:
  - This script is intentionally conservative: it only reads pages that are
    explicitly meant to advertise open positions to the public, and it does
    not attempt to log in, bypass paywalls, or scrape sites that disallow it
    (e.g. Indeed, LinkedIn) — those require official partnerships/APIs.
  - Each source is wrapped in its own try/except so that if one site changes
    its layout, the others still update instead of the whole run failing.
  - Add new sources by writing a new fetch_* function that returns a list of
    job dicts (see the `Job` shape below) and adding it to `SOURCES`.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Keywords used to filter broad sources (like USAJOBS) down to relevant roles.
# Not used for ABS/ISAE since those boards are already 100% on-topic.
KEYWORDS = [
    "animal behavior", "animal behaviour", "animal cognition",
    "comparative cognition", "comparative psychology", "ethology",
    "applied ethology", "animal welfare", "behavioral ecology",
    "behavioural ecology", "neuroethology", "wildlife biologist",
    "zoo behavior", "zoo behaviour", "anthrozoology",
    "human-animal interaction", "animal enrichment",
]

# A handful of narrower queries sent to USAJOBS (keep this list short —
# each one is a separate API call).
USAJOBS_QUERIES = [
    "animal behavior", "wildlife biologist", "animal welfare",
    "zoo", "animal care", "ethology",
]

HEADERS = {"User-Agent": "animal-behavior-job-board/1.0 (personal project)"}
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data.json")


def matches_keywords(*texts):
    blob = " ".join(t for t in texts if t).lower()
    return any(k in blob for k in KEYWORDS)


def parse_date_safe(text):
    """Try to parse a date string; return an ISO date or None."""
    if not text:
        return None
    try:
        dt = dateparser.parse(text, fuzzy=True, default=datetime(2026, 1, 1))
        return dt.date().isoformat()
    except (ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Source 1: USAJOBS API (official, requires free API key)
# https://developer.usajobs.gov/
# ---------------------------------------------------------------------------

def fetch_usajobs():
    email = os.environ.get("USAJOBS_EMAIL")
    api_key = os.environ.get("USAJOBS_API_KEY")
    if not email or not api_key:
        print("  USAJOBS: skipped (no USAJOBS_EMAIL / USAJOBS_API_KEY set)")
        return []

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": email,
        "Authorization-Key": api_key,
    }

    jobs = {}
    for query in USAJOBS_QUERIES:
        try:
            resp = requests.get(
                "https://data.usajobs.gov/api/search",
                params={"Keyword": query, "ResultsPerPage": 100},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            items = resp.json().get("SearchResult", {}).get("SearchResultItems", [])
        except Exception as e:
            print(f"  USAJOBS: query '{query}' failed: {e}")
            continue

        for item in items:
            d = item.get("MatchedObjectDescriptor", {})
            job_id = d.get("PositionID") or d.get("PositionURI")
            if not job_id or job_id in jobs:
                continue
            title = d.get("PositionTitle", "")
            org = d.get("OrganizationName", "")
            summary = d.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
            if not matches_keywords(title, summary):
                continue
            jobs[job_id] = {
                "title": title,
                "org": org,
                "location": d.get("PositionLocationDisplay", ""),
                "source": "USAJOBS",
                "category": "Federal government",
                "url": d.get("PositionURI", ""),
                "date_posted": d.get("PublicationStartDate", "")[:10] or None,
            }
    print(f"  USAJOBS: {len(jobs)} matching jobs")
    return list(jobs.values())


# ---------------------------------------------------------------------------
# Source 2: Animal Behavior Society — Positions & News
# https://www.animalbehaviorsociety.org/web/news.php
# ---------------------------------------------------------------------------

def fetch_abs():
    url = "https://www.animalbehaviorsociety.org/web/news.php"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ABS: failed to load page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.find_all("a", href=re.compile(r"news\.php\?view="))

    jobs = []
    seen = set()
    date_re = re.compile(r"\b[A-Z][a-z]{2}\s+\d{1,2}\s*$")

    for a in links:
        href = urljoin(url, a.get("href", ""))
        if href in seen:
            continue
        seen.add(href)
        title = a.get_text(strip=True)
        if not title:
            continue

        # Walk up to a container row and pull its full text to find the
        # category label and trailing date (e.g. "... Jobs & Postdocs  Sep 2").
        row = a
        row_text = ""
        for _ in range(4):
            row = row.parent
            if row is None:
                break
            row_text = row.get_text(" ", strip=True)
            if row_text and row_text != title:
                break

        date_match = date_re.search(row_text)
        date_str = date_match.group(0).strip() if date_match else None
        category = row_text
        if title in category:
            category = category.replace(title, "", 1).strip()
        if date_str:
            category = category[: -len(date_str)].strip()
        category = category or "Position"

        # Only keep job/postdoc/grad-position style postings, not general news.
        if not re.search(r"job|postdoc|position|grad", category, re.I):
            continue

        jobs.append({
            "title": title,
            "org": "",
            "location": "",
            "source": "Animal Behavior Society",
            "category": category,
            "url": href,
            "date_posted": parse_date_safe(date_str),
        })

    print(f"  ABS: {len(jobs)} postings")
    return jobs


# ---------------------------------------------------------------------------
# Source 3: ISAE (International Society for Applied Ethology)
# https://www.applied-ethology.org/Employment_and_Education.html
# ---------------------------------------------------------------------------

def fetch_isae():
    urls = [
        "https://www.applied-ethology.org/Employment_and_Education.html",
        "https://www.applied-ethology.org/iqs/rp.1/Employment_and_Education.html",  # page 2
    ]

    date_re = re.compile(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s+20\d{2}\b"
    )

    jobs = []
    seen = set()

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  ISAE: failed to load {url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if "applied-ethology.org" not in href:
                continue
            title = a.get_text(strip=True)
            if not title:
                continue

            # A real job listing sits right next to a date. Nav links don't.
            container = a
            nearby_text = ""
            for _ in range(3):
                container = container.parent
                if container is None:
                    break
                nearby_text = container.get_text(" ", strip=True)
                if date_re.search(nearby_text):
                    break

            date_match = date_re.search(nearby_text)
            if not date_match:
                continue  # not a dated listing -> probably nav/footer link

            if href in seen:
                continue
            seen.add(href)

            heading = a.find_previous(["h1", "h2", "h3"])
            category = heading.get_text(strip=True) if heading else "Opportunity"

            jobs.append({
                "title": title,
                "org": "",
                "location": "",
                "source": "ISAE (Applied Ethology)",
                "category": category,
                "url": href,
                "date_posted": parse_date_safe(date_match.group(0)),
            })

    print(f"  ISAE: {len(jobs)} postings")
    return jobs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SOURCES = [
    ("USAJOBS", fetch_usajobs),
    ("Animal Behavior Society", fetch_abs),
    ("ISAE", fetch_isae),
]


def main():
    all_jobs = []
    for name, fn in SOURCES:
        print(f"Fetching: {name}")
        try:
            all_jobs.extend(fn())
        except Exception as e:
            # A single source should never take down the whole run.
            print(f"  {name}: unexpected error, skipping ({e})")

    # Sort newest first; undated postings go last.
    all_jobs.sort(key=lambda j: j.get("date_posted") or "0000-00-00", reverse=True)

    for i, job in enumerate(all_jobs):
        job["id"] = i

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_jobs),
        "jobs": all_jobs,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(all_jobs)} jobs to {OUTPUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
