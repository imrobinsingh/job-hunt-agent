"""
Feedback learning — reads user decisions from Notion to improve AI scoring.

Learns from:
- Applied / Shortlisted / Interview = positive signals
- Rejected / Withdrawn = negative signals

Builds a preference profile that biases future relevance scoring.
"""
import json
import os
from pathlib import Path

from scraper.notion_sync import get_client

FEEDBACK_PATH = Path(__file__).parent.parent / "data" / "feedback_history.json"


def load_feedback() -> dict:
    """Load cached feedback history from disk."""
    if FEEDBACK_PATH.exists():
        try:
            return json.loads(FEEDBACK_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return {"positive": [], "negative": [], "last_sync": ""}
    return {"positive": [], "negative": [], "last_sync": ""}


def save_feedback(feedback: dict):
    """Persist feedback history to disk."""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(feedback, indent=2, ensure_ascii=False))


def sync_feedback_from_notion(
    database_id: str,
    positive_statuses: list[str],
    negative_statuses: list[str],
) -> dict:
    """
    Query Notion for jobs where user has set a status (Applied, Rejected, etc.)
    and extract patterns for the AI to learn from.
    """
    client = get_client()
    feedback = load_feedback()

    # Fetch jobs with positive statuses
    for status in positive_statuses:
        jobs = _query_by_status(client, database_id, status)
        for job in jobs:
            entry = _extract_entry(job)
            if entry and entry not in feedback["positive"]:
                feedback["positive"].append(entry)

    # Fetch jobs with negative statuses
    for status in negative_statuses:
        jobs = _query_by_status(client, database_id, status)
        for job in jobs:
            entry = _extract_entry(job)
            if entry and entry not in feedback["negative"]:
                feedback["negative"].append(entry)

    # Keep last 50 entries each to control prompt size
    feedback["positive"] = feedback["positive"][-50:]
    feedback["negative"] = feedback["negative"][-50:]

    save_feedback(feedback)
    return feedback


def build_preference_prompt(feedback: dict) -> str:
    """
    Convert feedback history into a prompt section that biases AI scoring.
    Returns empty string if no feedback exists.
    """
    lines = []

    if feedback.get("positive"):
        lines.append("## Jobs the user LIKED (applied to / shortlisted):")
        for entry in feedback["positive"][-20:]:
            lines.append(f"- {entry['title']} at {entry['company']} ({entry['location']})")

    if feedback.get("negative"):
        lines.append("\n## Jobs the user REJECTED:")
        for entry in feedback["negative"][-20:]:
            lines.append(f"- {entry['title']} at {entry['company']} ({entry['location']})")

    if lines:
        lines.insert(0, "# User's Past Preferences (learn from these patterns):\n")
        lines.append(
            "\nUse the patterns above to score new jobs higher/lower. "
            "For example, if the user consistently applies to Series A startups "
            "in Bangalore, score similar jobs higher."
        )

    return "\n".join(lines)


def _query_by_status(client, database_id: str, status: str) -> list[dict]:
    """Query Notion for jobs with a specific status."""
    try:
        resp = client.databases.query(
            database_id=database_id,
            filter={"property": "Status", "select": {"equals": status}},
            page_size=50,
        )
        return resp.get("results", [])
    except Exception as e:
        print(f"[memory] Error querying status '{status}': {e}")
        return []


def _extract_entry(page: dict) -> dict | None:
    """Extract a minimal job entry from a Notion page for feedback."""
    props = page.get("properties", {})

    title_parts = props.get("Name", {}).get("title", [])
    title = title_parts[0].get("plain_text", "") if title_parts else ""

    company_parts = props.get("Company", {}).get("rich_text", [])
    company = company_parts[0].get("plain_text", "") if company_parts else ""

    location = props.get("Location", {}).get("select", {})
    location_name = location.get("name", "") if location else ""

    stage = props.get("Company Stage", {}).get("select", {})
    stage_name = stage.get("name", "") if stage else ""

    position = props.get("Position", {}).get("select", {})
    position_name = position.get("name", "") if position else ""

    if not title:
        return None

    return {
        "title": title,
        "company": company,
        "location": location_name,
        "stage": stage_name,
        "position": position_name,
    }
