"""
iimjobs.com scraper — strong for senior CoS roles in India.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.iimjobs.com/j/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
SEARCH_TERMS = ["chief of staff", "founder office"]


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                BASE_URL,
                params={"q": term, "loc": "India"},
                headers=HEADERS,
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select(".job-card, article.job, .jobs-list-item, li.job")[:20]:
                link = card.select_one("a[href*='/j/']") or card.select_one("a[href*='iimjobs']")
                if not link:
                    continue
                href = link.get("href", "")
                url = f"https://www.iimjobs.com{href}" if href.startswith("/") else href
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title_el = card.select_one("h2, h3, .job-title, [class*='title']")
                company_el = card.select_one(".company-name, [class*='company']")
                location_el = card.select_one(".location, [class*='location']")

                title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location_raw = location_el.get_text(strip=True) if location_el else ""

                results.append({
                    "name": f"{company} — {title}",
                    "position": _classify_position(title),
                    "company": company,
                    "location": _map_location(location_raw),
                    "source": "iimjobs",
                    "job_url": url,
                    "date_found": datetime.utcnow().date().isoformat(),
                    "company_stage": "Unknown",
                    "ctc_range": _extract_ctc(card),
                })
        except Exception as e:
            print(f"[iimjobs] Error for '{term}': {e}")

    return results


def _classify_position(title: str) -> str:
    if "founder" in title.lower():
        return "Founder's Office"
    return "Chief of Staff"


def _map_location(loc: str) -> str:
    if not loc:
        return "Other"
    loc_lower = loc.lower()
    if any(x in loc_lower for x in ["delhi", "ncr", "gurgaon", "noida", "new delhi"]):
        return "Delhi NCR"
    if any(x in loc_lower for x in ["bangalore", "bengaluru"]):
        return "Bangalore"
    if "mumbai" in loc_lower:
        return "Mumbai"
    if "remote" in loc_lower:
        return "Remote"
    return "Other"


def _extract_ctc(card) -> str:
    ctc_el = card.select_one(".ctc, .salary, [class*='salary'], [class*='ctc']")
    if ctc_el:
        return ctc_el.get_text(strip=True)
    return ""
