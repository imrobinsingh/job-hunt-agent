"""
Remote OK — public JSON API, no auth needed.
"""
import requests
from datetime import datetime

API_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-hunt-agent/1.0)",
    "Accept": "application/json",
}
KEYWORDS = ["chief of staff", "founder", "founder's office"]


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        jobs = resp.json()

        for job in jobs:
            if not isinstance(job, dict):
                continue

            title = str(job.get("position") or "").lower()
            if not _is_relevant(title):
                continue

            url = job.get("url") or f"https://remoteok.com/jobs/{job.get('id', '')}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            company = job.get("company") or "Unknown"
            salary = _extract_salary(job)

            results.append({
                "name": f"{company} — {job.get('position', 'Chief of Staff')}",
                "position": _classify_position(title),
                "company": company,
                "location": "Remote",
                "source": "RemoteOK",
                "job_url": url,
                "date_found": datetime.utcnow().date().isoformat(),
                "company_stage": "Unknown",
                "ctc_range": salary,
            })
    except Exception as e:
        print(f"[remoteok] Error: {e}")

    return results


def _is_relevant(title: str) -> bool:
    return any(k in title for k in KEYWORDS)


def _classify_position(title: str) -> str:
    if "founder" in title:
        return "Founder's Office"
    return "Chief of Staff"


def _extract_salary(job: dict) -> str:
    min_sal = job.get("salary_min")
    max_sal = job.get("salary_max")
    if min_sal and max_sal:
        return f"${int(min_sal):,} – ${int(max_sal):,}/yr"
    return ""
