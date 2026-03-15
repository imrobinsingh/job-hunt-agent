"""
Cutshort.io scraper — best source for Indian funded startups.
Uses public search endpoint (no auth required).
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scraper.filters import is_relevant, classify_position

BASE_URL = "https://cutshort.io/api/v2/jobs/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://cutshort.io/",
}
SEARCH_TERMS = ["Chief of Staff", "Founder Office"]


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
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobs") or data.get("data") or data.get("results") or []
                for job in jobs:
                    _process_job(job, seen_urls, results)
            else:
                _scrape_html(term, seen_urls, results)
        except Exception as e:
            print(f"[cutshort] Error for '{term}': {e}")
            try:
                _scrape_html(term, seen_urls, results)
            except Exception as e2:
                print(f"[cutshort html] Error: {e2}")

    return results


def _process_job(job: dict, seen_urls: set, results: list):
    url = job.get("url") or job.get("job_url") or ""
    if not url.startswith("http"):
        slug = job.get("slug") or job.get("id", "")
        url = f"https://cutshort.io/job/{slug}"
    if not url or url in seen_urls:
        return

    title = str(job.get("title") or job.get("role") or "").strip()
    if not title or not is_relevant(title):
        return

    # Secondary guard: Cutshort API sometimes returns wrong titles (matches on skills/tags).
    # The URL slug always reflects the actual job title — validate it too.
    slug = url.split("/job/")[-1].lower()
    if not any(kw in slug for kw in ["chief", "founder", "head-of-staff"]):
        return

    seen_urls.add(url)

    # Extract company name — handle both dict and string forms
    company_raw = job.get("company") or job.get("company_name") or {}
    if isinstance(company_raw, dict):
        company = (
            company_raw.get("name")
            or company_raw.get("display_name")
            or company_raw.get("slug")
            or "Unknown"
        )
        funding = company_raw.get("funding_stage", "")
    else:
        company = str(company_raw).strip() or "Unknown"
        funding = ""

    locations = job.get("locations") or [job.get("location", "")]
    location = _map_location(locations[0] if locations else "")
    posted_raw = job.get("posted_at") or job.get("created_at") or job.get("publishedAt") or ""
    posted_date = str(posted_raw)[:10] if posted_raw else ""

    results.append({
        "name": f"{company} — {title}",
        "position": classify_position(title),
        "company": company,
        "location": location,
        "source": "Cutshort",
        "job_url": url,
        "date_found": datetime.utcnow().date().isoformat(),
        "posted_date": posted_date,
        "company_stage": _map_stage(funding),
        "ctc_range": _extract_ctc(job),
    })


def _scrape_html(term: str, seen_urls: set, results: list):
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
        title_el = card.select_one("h2, h3, [class*='title']")
        company_el = card.select_one("[class*='company']")
        title = title_el.get_text(strip=True) if title_el else term
        company = company_el.get_text(strip=True) if company_el else "Unknown"
        if not is_relevant(title):
            continue
        seen_urls.add(url)
        results.append({
            "name": f"{company} — {title}",
            "position": classify_position(title),
            "company": company,
            "location": "India",
            "source": "Cutshort",
            "job_url": url,
            "date_found": datetime.utcnow().date().isoformat(),
            "posted_date": "",
            "company_stage": "Unknown",
            "ctc_range": "",
        })


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
    if "series a" in f: return "Series A"
    if "series b" in f: return "Series B"
    if "series c" in f: return "Series C"
    if "series d" in f or "series e" in f: return "Series D+"
    if "unicorn" in f or "ipo" in f: return "Unicorn"
    if any(x in f for x in ["bootstrap", "self", "revenue"]): return "Bootstrap"
    return "Unknown"


def _extract_ctc(job: dict) -> str:
    min_ctc = job.get("min_ctc") or job.get("salary_min")
    max_ctc = job.get("max_ctc") or job.get("salary_max")
    if min_ctc and max_ctc:
        return f"₹{int(min_ctc)//100000}L – ₹{int(max_ctc)//100000}L"
    return ""
