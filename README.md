# Job Hunt Agent — CoS & Founder's Office

Scrapes 6 job boards every 3 hours and pushes new listings to a Notion database.
Runs free on GitHub Actions.

## Sources
| Board | Coverage |
|---|---|
| LinkedIn + Indeed | via JobSpy |
| Cutshort | Indian funded startups |
| iimjobs | Senior India roles |
| Wellfound | Series A–C global |
| We Work Remotely | Remote global |
| Remote OK | Remote global |

---

## One-time Setup

### 1. Get your Notion token
1. Go to https://www.notion.so/my-integrations
2. Create a new integration → copy the **Internal Integration Secret**
3. Open your **Job Hunt 2026** Notion page → click `...` → **Add connections** → add your integration

### 2. Clone & configure locally
```bash
git clone <your-repo-url>
cd job-hunt-agent
cp .env.example .env
# Edit .env — replace NOTION_TOKEN with your real secret
```

### 3. Create the Notion database
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
# Copy the printed NOTION_DATABASE_ID into your .env
```

### 4. Push to GitHub
```bash
git init   # if not already a repo
git add .
git commit -m "feat: initial job hunt agent"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 5. Add GitHub Secrets
In your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `NOTION_TOKEN` | Your Notion integration secret |
| `NOTION_DATABASE_ID` | From step 3 output |

### 6. Enable GitHub Actions
Go to **Actions** tab in your repo → enable workflows if prompted.

---

## Manual run (local test)
```bash
python -m scraper.main
```

## Manual trigger (GitHub)
Go to **Actions → Job Hunt Scraper → Run workflow**

---

## Notion database fields
| Field | Type | Description |
|---|---|---|
| Name | Title | Company — Position |
| Position | Select | Chief of Staff / Founder's Office |
| Company | Text | |
| Location | Select | Delhi NCR, Bangalore, Remote, etc. |
| Company Stage | Select | Series A/B/C/D+/Unicorn/Bootstrap |
| Source | Select | Which job board |
| Job URL | URL | Direct link |
| Date Found | Date | Auto-set |
| Status | Select | New → Applied → Interview → Offer |
| Applied Date | Date | Set manually when you apply |
| CTC Range | Text | From listing if available |
| Interview Scheduled | Checkbox | |
| Interview Date | Date | |
| Interview Time | Text | |
| Interview Link | URL | |
| Questions & Answers | Text | Paste prep notes |
| Notes | Text | Free text |
