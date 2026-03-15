"""
Cutshort.io scraper — best source for Indian funded startups.
Uses public search endpoint (no auth required).
"""
import requests
from datetime import datetime

BASE_URL = "https://cutshort.io/api/v2/jobs/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-hunt-agent/1.0)",
    "Accept": "application/json",
}
SEARCH_TERMS = ["Chief of Staff", "Founder Office"]


def _map_location(loc: str) -> str:
    if not loc:
        return "Other"
    loc_lower = loc.lower()
    if any(x in loc_lower for x in ["delhi", "ncr", "gurgaon", "noida"]):
        return "Delhi NCR"
    if any(x in loc_lower for x in ["bangalore", "bengaluru"]):
        return "Bangalore"
    if "mumbai" in loc_lower:
        return "Mumbai"
    if "remote" in loc_lower:
        return "Remote"
    return "Other"


def _map_stage(funding: str) -> str:
    if not funding:
        return "Unknown"
    f = funding.lower()
    if "series a" in f:
        return "Series A"
    if "series b" in f:
        return "Series B"
    if "series c" in f:
        return "Series C"
    if "series d" in f or "series e" in f:
        return "Series D+"
    if "unicorn" in f or "ipo" in f:
        return "Unicorn"
    if any(x in f for x in ["bootstrap", "self", "revenue"]):
        return "Bootstrap"
    return "Unknown"


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                BASE_URL,
                params={"q": term, "location": "India", "page": 1, "limit": 30},
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                # Fallback: scrape search page
                results.extend(_scrape_search_page(term, seen_urls))
                continue

            data = resp.json()
            jobs = data.get("jobs") or data.get("data") or data.get("results") or []

            for job in jobs:
                url = job.get("url") or job.get("job_url") or ""
                if not url.startswith("http"):
                    slug = job.get("slug") or job.get("id", "")
                    url = f"https://cutshort.io/job/{slug}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                company = job.get("company", {})
                company_name = company.get("name") if isinstance(company, dict) else str(company)
                title = job.get("title") or job.get("role", "")
                locations = job.get("locations") or [job.get("location", "")]
                location = _map_location(locations[0] if locations else "")
                funding = company.get("funding_stage", "") if isinstance(company, dict) else ""

                posted_raw = job.get("posted_at") or job.get("created_at") or job.get("publishedAt") or ""
                posted_date = str(posted_raw)[:10] if posted_raw else ""

                results.append({
                    "name": f"{company_name} — {title}",
                    "position": _classify_position(title),
                    "company": company_name,
                    "location": location,
                    "source": "Cutshort",
                    "job_url": url,
                    "date_found": datetime.utcnow().date().isoformat(),
                    "posted_date": posted_date,
                    "company_stage": _map_stage(funding),
                    "ctc_range": _extract_ctc(job),
                })
        except Exception as e:
            print(f"[cutshort] Error for '{term}': {e}")

    return results


def _scrape_search_page(term: str, seen_urls: set) -> list[dict]:
    """HTML fallback scraper for Cutshort search."""
    from bs4 import BeautifulSoup

    results = []
    try:
        resp = requests.get(
            f"https://cutshort.io/jobs?q={term.replace(' ', '+')}&location=India",
            headers={**HEADERS, "Accept": "text/html"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        for card in soup.select("a[href*='/job/']")[:20]:
            href = card.get("href", "")
            url = f"https://cutshort.io{href}" if href.startswith("/") else href
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title_el = card.select_one("h2, h3, [class*='title']")
            company_el = card.select_one("[class*='company']")
            title = title_el.get_text(strip=True) if title_el else term
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            results.append({
                "name": f"{company} — {title}",
                "position": _classify_position(title),
                "company": company,
                "location": "India",
                "source": "Cutshort",
                "job_url": url,
                "date_found": datetime.utcnow().date().isoformat(),
                "company_stage": "Unknown",
                "ctc_range": "",
            })
    except Exception as e:
        print(f"[cutshort html] Error: {e}")
    return results


def _classify_position(title: str) -> str:
    if "founder" in title.lower():
        return "Founder's Office"
    return "Chief of Staff"


def _extract_ctc(job: dict) -> str:
    min_ctc = job.get("min_ctc") or job.get("salary_min")
    max_ctc = job.get("max_ctc") or job.get("salary_max")
    if min_ctc and max_ctc:
        return f"₹{int(min_ctc)//100000}L – ₹{int(max_ctc)//100000}L"
    return ""
