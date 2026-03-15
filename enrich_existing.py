"""
Backfill AI enrichment for existing Notion rows that have no AI Score.
Run once: python enrich_existing.py

This fetches all jobs where AI Score is empty, runs AI analysis,
and updates the Notion pages in batches.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from scraper.notion_sync import get_client
from notion_client.errors import APIResponseError
from ai.pipeline import analyse_batch


def fetch_unenriched_jobs(database_id: str) -> list[dict]:
    """Fetch all Notion jobs that have no AI Score yet."""
    client = get_client()
    jobs = []
    cursor = None

    print("Fetching jobs without AI enrichment from Notion...")

    while True:
        kwargs = {
            "database_id": database_id,
            "page_size": 100,
            "filter": {
                "property": "AI Score",
                "number": {"is_empty": True},
            },
        }
        if cursor:
            kwargs["start_cursor"] = cursor

        resp = client.databases.query(**kwargs)

        for page in resp.get("results", []):
            props = page.get("properties", {})

            title_parts = props.get("Name", {}).get("title", [])
            name = title_parts[0].get("plain_text", "") if title_parts else ""

            company_parts = props.get("Company", {}).get("rich_text", [])
            company = company_parts[0].get("plain_text", "") if company_parts else ""

            location = (props.get("Location", {}).get("select") or {}).get("name", "")
            stage = (props.get("Company Stage", {}).get("select") or {}).get("name", "")
            position = (props.get("Position", {}).get("select") or {}).get("name", "")
            source = (props.get("Source", {}).get("select") or {}).get("name", "")
            ctc_parts = props.get("CTC Range", {}).get("rich_text", [])
            ctc = ctc_parts[0].get("plain_text", "") if ctc_parts else ""
            url = props.get("Job URL", {}).get("url", "")

            if name:
                jobs.append({
                    "name": name,
                    "company": company,
                    "position": position,
                    "location": location,
                    "source": source,
                    "company_stage": stage,
                    "ctc_range": ctc,
                    "job_url": url,
                    "_page_id": page["id"],
                })

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    return jobs


def update_notion_page(page_id: str, ai_data: dict):
    """Update a Notion page with AI-enriched fields."""
    client = get_client()

    properties = {}

    if ai_data.get("ai_score") is not None:
        properties["AI Score"] = {"number": ai_data["ai_score"]}

    if ai_data.get("ai_match_score") is not None:
        properties["Match Score"] = {"number": ai_data["ai_match_score"]}

    if ai_data.get("ai_summary"):
        properties["Summary"] = {
            "rich_text": [{"text": {"content": ai_data["ai_summary"][:2000]}}]
        }

    if ai_data.get("ai_why_fit"):
        properties["Why I'm a Fit"] = {
            "rich_text": [{"text": {"content": ai_data["ai_why_fit"][:2000]}}]
        }

    if ai_data.get("ai_key_requirements"):
        reqs = " | ".join(ai_data["ai_key_requirements"][:10])
        properties["Key Requirements"] = {
            "rich_text": [{"text": {"content": reqs[:2000]}}]
        }

    if ai_data.get("ai_red_flags"):
        flags = " | ".join(ai_data["ai_red_flags"][:5])
        if flags:
            properties["Red Flags"] = {
                "rich_text": [{"text": {"content": flags[:2000]}}]
            }

    if not properties:
        return

    try:
        client.pages.update(page_id=page_id, properties=properties)
    except APIResponseError as e:
        print(f"  [notion] Failed to update page {page_id}: {e}")


def main():
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print("ERROR: NOTION_DATABASE_ID not set.")
        sys.exit(1)

    jobs = fetch_unenriched_jobs(database_id)
    if not jobs:
        print("No jobs need enrichment — all rows already have AI scores.")
        return

    print(f"Found {len(jobs)} jobs to enrich\n")

    # Run AI analysis in batches
    enriched = analyse_batch(jobs)

    # Update Notion pages
    updated = 0
    for job in enriched:
        page_id = job.get("_page_id")
        if not page_id:
            continue

        has_ai = any(job.get(k) for k in ["ai_score", "ai_summary", "ai_why_fit"])
        if not has_ai:
            continue

        print(f"  Updating: {job.get('name', '?')[:60]} (score: {job.get('ai_score', '?')}, match: {job.get('ai_match_score', '?')})")
        update_notion_page(page_id, job)
        updated += 1

    print(f"\nDone — {updated}/{len(jobs)} jobs enriched with AI data")


if __name__ == "__main__":
    main()
