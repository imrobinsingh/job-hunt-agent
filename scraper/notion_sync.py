"""
Pushes new jobs to Notion. Deduplicates by Job URL.
"""
import os
from notion_client import Client
from notion_client.errors import APIResponseError

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise ValueError("NOTION_TOKEN environment variable not set")
        _client = Client(auth=token)
    return _client


def get_existing_urls(database_id: str) -> set[str]:
    """Fetch all job URLs already in the database."""
    client = get_client()
    seen = set()
    cursor = None

    while True:
        kwargs = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)

        for page in resp.get("results", []):
            props = page.get("properties", {})
            url_prop = props.get("Job URL", {})
            url = url_prop.get("url") or ""
            if url:
                seen.add(url)

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    return seen


def push_job(database_id: str, job: dict) -> bool:
    """Create a new page (row) in the Notion database for a job."""
    client = get_client()

    properties = {
        "Name": {"title": [{"text": {"content": job.get("name", "")[:100]}}]},
        "Company": {"rich_text": [{"text": {"content": job.get("company", "")[:100]}}]},
        "Job URL": {"url": job.get("job_url") or None},
        "Date Found": {"date": {"start": job.get("date_found")} if job.get("date_found") else None},
        "Status": {"select": {"name": "New"}},
        "Interview Scheduled": {"checkbox": False},
    }

    if job.get("position"):
        properties["Position"] = {"select": {"name": job["position"]}}

    if job.get("location"):
        properties["Location"] = {"select": {"name": job["location"]}}

    if job.get("company_stage"):
        properties["Company Stage"] = {"select": {"name": job["company_stage"]}}

    if job.get("source"):
        source = job["source"]
        # Normalise source names to match select options
        source_map = {
            "Linkedin": "LinkedIn",
            "linkedin": "LinkedIn",
            "indeed": "Indeed",
            "Indeed": "Indeed",
        }
        properties["Source"] = {"select": {"name": source_map.get(source, source)}}

    if job.get("ctc_range"):
        properties["CTC Range"] = {"rich_text": [{"text": {"content": job["ctc_range"][:100]}}]}

    if job.get("posted_date"):
        properties["Posted Date"] = {"date": {"start": job["posted_date"]}}

    # Remove None date values
    if properties.get("Date Found", {}).get("date") is None:
        del properties["Date Found"]

    try:
        client.pages.create(parent={"database_id": database_id}, properties=properties)
        return True
    except APIResponseError as e:
        print(f"[notion] Failed to push '{job.get('name')}': {e}")
        return False


def sync_jobs(database_id: str, jobs: list[dict]) -> tuple[int, int]:
    """
    Sync a list of jobs to Notion, skipping duplicates.
    Returns (added, skipped) counts.
    """
    existing_urls = get_existing_urls(database_id)
    added = 0
    skipped = 0

    for job in jobs:
        url = job.get("job_url", "")
        if url and url in existing_urls:
            skipped += 1
            continue
        if push_job(database_id, job):
            added += 1
            if url:
                existing_urls.add(url)
        else:
            skipped += 1

    return added, skipped
