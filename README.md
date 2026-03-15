<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=160&section=header&text=Job%20Hunt%20Agent&fontSize=40&fontColor=fff&animation=twinkling&fontAlignY=38&desc=AI-powered%20job%20scraper%20%E2%86%92%20Notion%20DB&descAlignY=58&descSize=16" />
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/AI-Gemini%20Flash-4285F4?style=flat-square&logo=google&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/DB-Notion-000000?style=flat-square&logo=notion&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Hosting-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Cost-100%25%20Free-22C55E?style=flat-square" /></a>
</p>

<p align="center">
  <strong>Scrapes jobs from 4+ sources every 3 hours → scores them with AI → pushes to your Notion DB.<br/>Learns from your decisions over time. Totally free to run.</strong>
</p>

---

## What It Does

You're hunting for a specific role. Hundreds of listings get posted daily across LinkedIn, Cutshort, Indeed, RemoteOK, and more. Most are noise. This agent:

1. **Scrapes** 4+ job boards every 3 hours via GitHub Actions (free)
2. **AI scores** each job 0–100 for relevance to your profile
3. **Summarises** job descriptions so you don't have to read everything
4. **Matches** your resume against each JD and generates a personalised *"Why I'm a Fit"* note
5. **Learns** — when you mark jobs Applied or Rejected in Notion, the next run adjusts scoring based on your patterns
6. **Pushes** everything to a Notion database with zero duplicates

**Total running cost: ₹0 / $0 forever.**

---

## Notion DB Preview

Every job gets these AI-enriched columns automatically:

| Column | What it shows |
|---|---|
| **AI Score** | 0–100 relevance to your search |
| **Match Score** | 0–100 resume-to-JD match |
| **Summary** | 2–3 sentence JD digest |
| **Why I'm a Fit** | Personalised fit note using your resume |
| **Key Requirements** | Top skills/experience the role needs |
| **Red Flags** | Anything concerning in the listing |
| **Status** | New → Shortlisted → Applied → Interview → Offer / Rejected |

---

## Setup (< 5 minutes)

### Prerequisites
- Python 3.11+
- A free [Notion account](https://notion.so)
- A free [Gemini API key](https://aistudio.google.com/app/apikey) — Google AI Studio, no credit card needed

### Step 1 — Fork & clone

```bash
git clone https://github.com/imrobinsingh/job-hunt-agent.git
cd job-hunt-agent
```

### Step 2 — Create your Notion integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration** → give it a name → copy the **Internal Integration Secret**
3. Create a blank page in Notion where your Job Tracker will live → copy the **Page ID** from the URL
   - URL format: `notion.so/My-Page-32402fc2...` → the hex string at the end is the ID
4. Open that page → click `···` (top right) → **Connections** → add your integration

### Step 3 — Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
NOTION_TOKEN=ntn_your_integration_secret
NOTION_PAGE_ID=your_page_id_here
NOTION_DATABASE_ID=             # leave blank — filled by setup.py
GEMINI_API_KEY=your_gemini_key  # from https://aistudio.google.com/app/apikey
```

### Step 4 — Customise your search

Edit **`config.yaml`** — the only file you need to touch:

```yaml
roles:
  required_keywords:
    - "chief of staff"
    - "founder's office"

priorities:
  - "Series A–C funded startups"
  - "Direct access to founders"
  - "₹30L+ CTC"

experience_years: 6
```

### Step 5 — Add your resume

Edit **`profile/resume.md`** with your actual experience. The AI uses this to score how well you match each job and generate fit notes.

### Step 6 — Create the Notion database

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python setup.py
```

Copy the printed `NOTION_DATABASE_ID` back into your `.env`.

### Step 7 — Run it locally

```bash
python -m scraper.main
```

Jobs should appear in your Notion DB within ~2 minutes.

### Step 8 — Deploy on GitHub Actions (runs free, every 3 hours)

Add these 3 secrets to your repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `NOTION_TOKEN` | Your Notion integration secret |
| `NOTION_DATABASE_ID` | Output from `setup.py` |
| `GEMINI_API_KEY` | Your Google AI Studio key |

Done. The scraper runs 8× a day automatically, forever, for free.

---

## Backfill Existing Jobs with AI

Already have jobs in Notion without AI scores? Run:

```bash
python enrich_existing.py
```

Fetches all rows with an empty AI Score and enriches them in batches.

---

## How the AI Learns

Every run, the agent queries your Notion DB for status changes:

- **Applied / Shortlisted / Interview** → positive signal
- **Rejected / Withdrawn** → negative signal

It builds a preference profile from your decisions and biases future scoring. The more you use it, the smarter the scoring gets.

Feedback is cached in `data/feedback_history.json` and auto-committed to your repo after each GitHub Actions run.

---

## Architecture

```
GitHub Actions (8× / day, free for public repos)
        │
        ▼
scraper/main.py — orchestrator
        │
        ├── sources/linkedin_guest.py   ← LinkedIn (no auth)
        ├── sources/jobspy_scraper.py   ← LinkedIn + Indeed
        ├── sources/cutshort.py         ← Indian funded startups
        └── sources/remoteok.py         ← Remote jobs
        │
        ▼
Deduplicate by URL
        │
        ▼
ai/memory.py ← read Applied/Rejected from Notion
        │
        ▼
ai/pipeline.py ← batch Gemini calls (5 jobs / API call)
  ├── ai/jd_fetcher.py   ← scrape JD text from listing URL
  └── ai/client.py       ← Gemini Flash (auto-fallback across 4 models)
        │
        ▼
scraper/notion_sync.py → Notion DB (dedup by URL)
```

**AI efficiency:** 33 jobs = 7 API calls (not 33). Stays well within free tier (500 req/day).

**Model fallback chain:** `gemini-2.0-flash-lite` → `gemini-2.0-flash` → `gemini-2.5-flash` → `gemini-flash-lite-latest`. Auto-switches when one model hits its quota.

---

## Free Tier Limits

| Service | Limit | Our Usage |
|---|---|---|
| GitHub Actions | Unlimited for public repos | ~20 min/day |
| Gemini API | 500 req/day, 1M tokens/day | ~56 req/day |
| Notion API | Unlimited | ~50–200 writes/day |

Comfortably free, even at 2× the scrape frequency.

---

## Adding a New Job Source

Each scraper is a single file with a `fetch() -> list[dict]` interface:

```python
# scraper/sources/my_source.py
from datetime import datetime
from scraper.filters import is_relevant, classify_position

def fetch() -> list[dict]:
    jobs = []
    # ... your scraping logic ...
    for item in raw_results:
        title = item["title"]
        if not is_relevant(title):
            continue
        jobs.append({
            "name": f"{item['company']} — {title}",
            "company": item["company"],
            "position": classify_position(title),
            "location": "Bangalore",
            "source": "MySource",
            "job_url": item["url"],
            "date_found": datetime.utcnow().date().isoformat(),
            "posted_date": "",
            "company_stage": "Unknown",
            "ctc_range": "",
        })
    return jobs
```

Register it in `scraper/main.py`:
```python
from scraper.sources import my_source

SCRAPERS = [
    ...
    ("My Source", my_source.fetch),
]
```

---

## Notion Fields Reference

| Field | Type | Auto / Manual |
|---|---|---|
| Name | Title | Auto |
| Position | Select | Auto |
| Company | Text | Auto |
| Location | Select | Auto |
| Company Stage | Select | Auto |
| Source | Select | Auto |
| Job URL | URL | Auto |
| Date Found | Date | Auto |
| Job Posted | Date | Auto (if available) |
| CTC Range | Text | Auto (if available) |
| AI Score | Number | Auto — AI |
| Match Score | Number | Auto — AI |
| Summary | Text | Auto — AI |
| Why I'm a Fit | Text | Auto — AI |
| Key Requirements | Text | Auto — AI |
| Red Flags | Text | Auto — AI |
| Status | Select | **You set this** |
| Applied Date | Date | Manual |
| Interview Scheduled | Checkbox | Manual |
| Interview Date | Date | Manual |
| Notes | Text | Manual |

---

## Built For

Out of the box: **Chief of Staff** and **Founder's Office** roles across India and Remote. The hardest roles to track — inconsistent titles, posted everywhere, gone fast.

Fully configurable for any role via `config.yaml`.

---

## Roadmap

- [ ] Naukri scraper
- [ ] iimjobs scraper
- [ ] Wellfound scraper
- [ ] Y Combinator Jobs scraper
- [ ] Instahyre scraper
- [ ] Slack / WhatsApp daily digest of top 5 matches
- [ ] Auto-draft cover letter snippets

PRs welcome.

---

## Licence

MIT — use it, fork it, build on it.

---

<p align="center">
  Built by <a href="https://github.com/imrobinsingh">Robin Singh</a>
  &nbsp;·&nbsp;
  <a href="https://www.linkedin.com/in/imrobinsingh/">LinkedIn</a>
  &nbsp;·&nbsp;
  <a href="https://x.com/im_robinsingh">X / Twitter</a>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=80&section=footer" />
</p>
