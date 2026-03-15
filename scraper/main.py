"""
Main orchestrator — runs all scrapers, AI analysis, and syncs results to Notion.
Called by GitHub Actions every 3 hours.

Pipeline:
  1. Scrape jobs from all sources
  2. Deduplicate within batch
  3. Learn from user's past decisions (Notion status)
  4. AI analysis: score, summarise, match (Gemini Flash — free tier)
  5. Filter by AI relevance score
  6. Sync to Notion with enriched fields
"""
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from scraper.sources import jobspy_scraper, cutshort, linkedin_guest, remoteok
from scraper.notion_sync import sync_jobs


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text()) or {}
    return {}


SCRAPERS = [
    ("LinkedIn Guest API", linkedin_guest.fetch),
    ("JobSpy (LinkedIn + Indeed)", jobspy_scraper.fetch),
    ("Cutshort", cutshort.fetch),
    ("RemoteOK", remoteok.fetch),
]


def _ai_enabled() -> bool:
    """Check if AI features are available (Gemini API key set + config enabled)."""
    config = _load_config()
    if not config.get("ai", {}).get("enabled", True):
        return False
    return bool(os.environ.get("GEMINI_API_KEY"))


def main():
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print("ERROR: NOTION_DATABASE_ID not set. Run setup.py first.")
        sys.exit(1)

    config = _load_config()
    all_jobs: list[dict] = []

    print("=" * 60)
    print("Job Hunt Agent — AI-Powered Job Intelligence")
    print("=" * 60)

    # --- Step 1: Scrape ---
    for name, fetch_fn in SCRAPERS:
        print(f"\n[{name}] Fetching...")
        try:
            jobs = fetch_fn()
            print(f"[{name}] Found {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[{name}] FAILED: {e}")

    # --- Step 2: Deduplicate ---
    seen = set()
    deduped = []
    for job in all_jobs:
        url = job.get("job_url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(job)

    print(f"\nTotal unique jobs this run: {len(deduped)}")

    # --- Step 3 & 4: AI analysis (if available) ---
    if _ai_enabled() and deduped:
        print("\n" + "-" * 60)
        print("[AI] Gemini Flash analysis enabled")
        print("-" * 60)

        from ai.memory import sync_feedback_from_notion, build_preference_prompt
        from ai.pipeline import analyse_batch

        # Learn from past decisions
        notion_config = config.get("notion", {})
        positive = notion_config.get("positive_statuses", ["Applied", "Shortlisted"])
        negative = notion_config.get("negative_statuses", ["Rejected", "Withdrawn"])

        print("[AI] Syncing feedback from Notion...")
        feedback = sync_feedback_from_notion(database_id, positive, negative)
        pos_count = len(feedback.get("positive", []))
        neg_count = len(feedback.get("negative", []))
        print(f"[AI] Feedback: {pos_count} positive, {neg_count} negative signals")

        preference_prompt = build_preference_prompt(feedback)

        # Analyse jobs
        print(f"[AI] Analysing {len(deduped)} jobs...")
        deduped = analyse_batch(deduped, preference_prompt)
        print(f"[AI] {len(deduped)} jobs passed AI filter")
    elif not _ai_enabled():
        print("\n[AI] Skipped — GEMINI_API_KEY not set (rule-based filtering only)")

    # --- Step 5: Sync to Notion ---
    print("\nSyncing to Notion...")
    added, skipped = sync_jobs(database_id, deduped)

    print(f"\n{'=' * 60}")
    print(f"Done — {added} new jobs added, {skipped} already existed")
    if _ai_enabled():
        print("AI enrichment: scores, summaries, match notes included")
    print("=" * 60)


if __name__ == "__main__":
    main()
