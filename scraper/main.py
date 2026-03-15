"""
Main orchestrator — runs all scrapers and syncs results to Notion.
Called by GitHub Actions every 3 hours.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from scraper.sources import jobspy_scraper, cutshort, linkedin_guest, remoteok
from scraper.notion_sync import sync_jobs

SCRAPERS = [
    ("LinkedIn Guest API", linkedin_guest.fetch),
    ("JobSpy (LinkedIn + Indeed)", jobspy_scraper.fetch),
    ("Cutshort", cutshort.fetch),
    ("RemoteOK", remoteok.fetch),
]


def main():
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print("ERROR: NOTION_DATABASE_ID not set. Run setup.py first.")
        sys.exit(1)

    all_jobs: list[dict] = []

    print("=" * 55)
    print("Job Hunt Agent — CoS & Founder's Office")
    print("=" * 55)

    for name, fetch_fn in SCRAPERS:
        print(f"\n[{name}] Fetching...")
        try:
            jobs = fetch_fn()
            print(f"[{name}] Found {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[{name}] FAILED: {e}")

    # Deduplicate within this batch by URL
    seen = set()
    deduped = []
    for job in all_jobs:
        url = job.get("job_url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(job)

    print(f"\nTotal unique jobs this run: {len(deduped)}")
    print("Syncing to Notion...")

    added, skipped = sync_jobs(database_id, deduped)

    print(f"\n✅ Done — {added} new jobs added, {skipped} already existed")
    print("=" * 55)


if __name__ == "__main__":
    main()
