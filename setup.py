"""
One-time setup: creates the Job Tracker database in your Notion page.
Run once: python setup.py
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = os.getenv("NOTION_PAGE_ID", "32402fc2049380c799d9e35038bcd35c")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

DATABASE_SCHEMA = {
    "parent": {"type": "page_id", "page_id": PAGE_ID},
    "icon": {"type": "emoji", "emoji": "📋"},
    "title": [{"type": "text", "text": {"content": "Job Tracker"}}],
    "properties": {
        "Name": {"title": {}},
        "Position": {
            "select": {
                "options": [
                    {"name": "Chief of Staff", "color": "blue"},
                    {"name": "Founder's Office", "color": "purple"},
                ]
            }
        },
        "Company": {"rich_text": {}},
        "Location": {
            "select": {
                "options": [
                    {"name": "Delhi NCR", "color": "green"},
                    {"name": "Bangalore", "color": "orange"},
                    {"name": "Remote", "color": "gray"},
                    {"name": "Mumbai", "color": "yellow"},
                    {"name": "Other", "color": "default"},
                ]
            }
        },
        "Company Stage": {
            "select": {
                "options": [
                    {"name": "Series A", "color": "blue"},
                    {"name": "Series B", "color": "purple"},
                    {"name": "Series C", "color": "pink"},
                    {"name": "Series D+", "color": "red"},
                    {"name": "Unicorn", "color": "yellow"},
                    {"name": "Bootstrap", "color": "green"},
                    {"name": "Unknown", "color": "gray"},
                ]
            }
        },
        "Source": {
            "select": {
                "options": [
                    {"name": "LinkedIn", "color": "blue"},
                    {"name": "Wellfound", "color": "orange"},
                    {"name": "Cutshort", "color": "green"},
                    {"name": "iimjobs", "color": "red"},
                    {"name": "Indeed", "color": "purple"},
                    {"name": "RemoteOK", "color": "pink"},
                    {"name": "WeWorkRemotely", "color": "yellow"},
                    {"name": "Instahyre", "color": "gray"},
                    {"name": "Naukri", "color": "default"},
                ]
            }
        },
        "Job URL": {"url": {}},
        "Date Found": {"date": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "New", "color": "blue"},
                    {"name": "Shortlisted", "color": "purple"},
                    {"name": "Applied", "color": "yellow"},
                    {"name": "Screening", "color": "orange"},
                    {"name": "Interview", "color": "green"},
                    {"name": "Offer", "color": "pink"},
                    {"name": "Rejected", "color": "red"},
                    {"name": "Withdrawn", "color": "gray"},
                ]
            }
        },
        "Applied Date": {"date": {}},
        "CTC Range": {"rich_text": {}},
        "Interview Scheduled": {"checkbox": {}},
        "Interview Date": {"date": {}},
        "Interview Time": {"rich_text": {}},
        "Interview Link": {"url": {}},
        "Questions & Answers": {"rich_text": {}},
        "Notes": {"rich_text": {}},
    },
}


def create_database():
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN not set in .env file")
        return

    resp = requests.post(
        "https://api.notion.com/v1/databases",
        headers=HEADERS,
        json=DATABASE_SCHEMA,
    )

    if resp.status_code == 200:
        db_id = resp.json()["id"]
        print(f"✅ Database created successfully!")
        print(f"   Database ID: {db_id}")
        print(f"\n👉 Add this to your .env file:")
        print(f"   NOTION_DATABASE_ID={db_id}")
        print(f"\n👉 Add this as a GitHub Actions secret:")
        print(f"   Name:  NOTION_DATABASE_ID")
        print(f"   Value: {db_id}")

        # Auto-write to .env if it exists
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                content = f.read()
            if "NOTION_DATABASE_ID=" in content:
                content = content.replace(
                    "NOTION_DATABASE_ID=", f"NOTION_DATABASE_ID={db_id}"
                )
                with open(env_path, "w") as f:
                    f.write(content)
                print(f"\n✅ .env updated automatically.")
    else:
        print(f"ERROR {resp.status_code}: {resp.json()}")


if __name__ == "__main__":
    create_database()
