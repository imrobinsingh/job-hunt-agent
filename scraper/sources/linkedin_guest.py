"""
LinkedIn Jobs via public guest API — no auth, no JobSpy dependency.
Catches recent postings sorted by date.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
SEARCHES = [
    {"keywords": "Chief of Staff", "location": "India"},
    {"keywords": "Founder's Office", "location": "India"},
    {"keywords": "Chief of Staff", "location": ""},  # global remote
]


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for search in SEARCHES:
        try:
            resp = requests.get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params={
                    "keywords": search["keywords"],
                    "location": search["location"],
                    "start": 0,
                    "sortBy": "DD",  # most recent first
                },
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("li"):
                link = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
                if not link:
                    continue
                url = link.get("href", "").split("?")[0]
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title_el = card.select_one("h3.base-search-card__title, h3")
                company_el = card.select_one("h4.base-search-card__subtitle, a[data-tracking-control-name*='company']")
                location_el = card.select_one("span.job-search-card__location")

                title = title_el.get_text(strip=True) if title_el else search["keywords"]
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location_raw = location_el.get_text(strip=True) if location_el else search.get("location", "")

                if not _is_relevant(title):
                    continue

                posted_el = card.select_one("time")
                posted_date = posted_el.get("datetime", "")[:10] if posted_el else ""

                results.append({
                    "name": f"{company} — {title}",
                    "position": _classify_position(title),
                    "company": company,
                    "location": _map_location(location_raw),
                    "source": "LinkedIn",
                    "job_url": url,
                    "date_found": datetime.utcnow().date().isoformat(),
                    "posted_date": posted_date,
                    "company_stage": "Unknown",
                    "ctc_range": "",
                })
        except Exception as e:
            print(f"[linkedin_guest] Error for '{search}': {e}")

    return results


def _is_relevant(title: str) -> bool:
    keywords = ["chief of staff", "founder's office", "founder office", "chief-of-staff"]
    return any(k in title.lower() for k in keywords)


def _classify_position(title: str) -> str:
    if "founder" in title.lower():
        return "Founder's Office"
    return "Chief of Staff"


def _map_location(loc: str) -> str:
    if not loc:
        return "Remote"
    loc_lower = loc.lower()
    if any(x in loc_lower for x in ["delhi", "ncr", "gurgaon", "noida", "new delhi"]):
        return "Delhi NCR"
    if any(x in loc_lower for x in ["bangalore", "bengaluru"]):
        return "Bangalore"
    if "mumbai" in loc_lower:
        return "Mumbai"
    if any(x in loc_lower for x in ["remote", "anywhere"]):
        return "Remote"
    if "india" in loc_lower:
        return "Other"
    return "Remote"
