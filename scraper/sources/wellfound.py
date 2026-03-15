"""
Wellfound (AngelList) scraper — best for Series A–C startups globally.
Uses public job listings page.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}
SEARCH_URLS = [
    "https://wellfound.com/role/l/chief-of-staff/india",
    "https://wellfound.com/role/r/chief-of-staff",
]


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for url in SEARCH_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select("div[class*='JobListing'], div[data-test*='job'], div[class*='job-listing']")[:25]:
                link = card.select_one("a[href*='/jobs/']") or card.select_one("a[href]")
                if not link:
                    continue
                href = link.get("href", "")
                job_url = f"https://wellfound.com{href}" if href.startswith("/") else href
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                title_el = card.select_one("h2, h3, span[class*='title'], div[class*='title']")
                company_el = card.select_one("a[class*='company'], span[class*='company'], div[class*='startup']")
                location_el = card.select_one("span[class*='location'], div[class*='location']")

                title = title_el.get_text(strip=True) if title_el else "Chief of Staff"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location_raw = location_el.get_text(strip=True) if location_el else ""

                if not _is_relevant(title):
                    continue

                results.append({
                    "name": f"{company} — {title}",
                    "position": _classify_position(title),
                    "company": company,
                    "location": _map_location(location_raw),
                    "source": "Wellfound",
                    "job_url": job_url,
                    "date_found": datetime.utcnow().date().isoformat(),
                    "company_stage": "Unknown",
                    "ctc_range": "",
                })
        except Exception as e:
            print(f"[wellfound] Error for {url}: {e}")

    return results


def _is_relevant(title: str) -> bool:
    keywords = ["chief of staff", "founder", "founder's office", "founder office"]
    return any(k in title.lower() for k in keywords)


def _classify_position(title: str) -> str:
    if "founder" in title.lower():
        return "Founder's Office"
    return "Chief of Staff"


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
    if any(x in loc_lower for x in ["remote", "anywhere"]):
        return "Remote"
    if "india" in loc_lower:
        return "Other"
    return "Remote"
