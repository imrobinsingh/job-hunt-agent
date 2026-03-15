"""
LinkedIn + Indeed scraper via JobSpy (free, no API key needed).
"""
from jobspy import scrape_jobs
from datetime import datetime
from scraper.filters import is_relevant, classify_position

SEARCH_TERMS = ["Chief of Staff", "Founder's Office"]
LOCATIONS = ["Delhi, India", "Bangalore, India", "India"]


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for term in SEARCH_TERMS:
        for location in LOCATIONS:
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=term,
                    location=location,
                    results_wanted=25,
                    hours_old=4,
                    country_indeed="India",
                )
                for _, row in jobs.iterrows():
                    url = str(row.get("job_url", "")).strip()
                    if not url or url in seen_urls:
                        continue

                    title = str(row.get("title", "")).strip()
                    if not title or not is_relevant(title):
                        continue

                    seen_urls.add(url)
                    company = str(row.get("company", "")).strip()
                    location_raw = str(row.get("location", "")).strip()
                    site = str(row.get("site", "")).strip().title()
                    posted = row.get("date_posted")
                    posted_date = str(posted)[:10] if posted else ""

                    results.append({
                        "name": f"{company} — {title}",
                        "position": classify_position(title),
                        "company": company,
                        "location": _map_location(location_raw),
                        "source": "LinkedIn" if "linkedin" in site.lower() else "Indeed",
                        "job_url": url,
                        "date_found": datetime.utcnow().date().isoformat(),
                        "posted_date": posted_date,
                        "company_stage": "Unknown",
                        "ctc_range": _extract_salary(row),
                    })
            except Exception as e:
                print(f"[jobspy] Error for '{term}' in '{location}': {e}")

    return results


def _map_location(loc_str: str) -> str:
    if not loc_str:
        return "Other"
    loc_lower = loc_str.lower()
    if any(x in loc_lower for x in ["delhi", "ncr", "gurgaon", "noida", "faridabad"]):
        return "Delhi NCR"
    if any(x in loc_lower for x in ["bangalore", "bengaluru"]):
        return "Bangalore"
    if "mumbai" in loc_lower:
        return "Mumbai"
    if any(x in loc_lower for x in ["remote", "anywhere"]):
        return "Remote"
    return "Other"


def _extract_salary(row) -> str:
    min_sal = row.get("min_amount")
    max_sal = row.get("max_amount")
    currency = row.get("currency", "INR")
    if min_sal and max_sal:
        return f"{currency} {int(min_sal):,} – {int(max_sal):,}"
    if min_sal:
        return f"{currency} {int(min_sal):,}+"
    return ""
