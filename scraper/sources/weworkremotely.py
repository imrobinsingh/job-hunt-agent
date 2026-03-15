"""
We Work Remotely — RSS feed scraper for remote CoS roles globally.
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_URLS = [
    "https://weworkremotely.com/remote-jobs/search.rss?term=chief+of+staff",
    "https://weworkremotely.com/remote-jobs/search.rss?term=founder+office",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-hunt-agent/1.0)"}


def fetch() -> list[dict]:
    results = []
    seen_urls = set()

    for rss_url in RSS_URLS:
        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            root = ET.fromstring(resp.content)

            for item in root.findall(".//item"):
                url = _get_text(item, "link") or _get_text(item, "guid")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title_raw = _get_text(item, "title") or ""
                # WWR titles are usually "Company: Role Title"
                if ": " in title_raw:
                    company, title = title_raw.split(": ", 1)
                else:
                    company, title = "Unknown", title_raw

                if not _is_relevant(title):
                    continue

                results.append({
                    "name": f"{company.strip()} — {title.strip()}",
                    "position": _classify_position(title),
                    "company": company.strip(),
                    "location": "Remote",
                    "source": "WeWorkRemotely",
                    "job_url": url,
                    "date_found": datetime.utcnow().date().isoformat(),
                    "company_stage": "Unknown",
                    "ctc_range": "",
                })
        except Exception as e:
            print(f"[weworkremotely] Error for {rss_url}: {e}")

    return results


def _get_text(element, tag: str) -> str:
    el = element.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _is_relevant(title: str) -> bool:
    keywords = ["chief of staff", "founder", "founder's office", "chief-of-staff"]
    return any(k in title.lower() for k in keywords)


def _classify_position(title: str) -> str:
    if "founder" in title.lower():
        return "Founder's Office"
    return "Chief of Staff"
