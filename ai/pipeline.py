"""
AI pipeline — batch Gemini calls for efficiency.
Sends 5 jobs per API call → 33 jobs = 7 calls (not 33).
Returns: relevance_score, summary, match_score, why_fit, key_requirements, red_flags.
"""
import os
import yaml
from pathlib import Path

from ai.client import generate
from ai.jd_fetcher import fetch_description
from ai.memory import build_preference_prompt

_config = None
_resume = None

BATCH_SIZE = 5  # jobs per API call


def _load_config() -> dict:
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            _config = yaml.safe_load(config_path.read_text())
        else:
            _config = {}
    return _config


def _load_resume() -> str:
    global _resume
    if _resume is None:
        resume_path = Path(__file__).parent.parent / "profile" / "resume.md"
        if resume_path.exists():
            # Keep to 1000 chars — fits comfortably in batch prompt
            _resume = resume_path.read_text().strip()[:1000]
        else:
            _resume = ""
    return _resume


def analyse_batch(jobs: list[dict], preference_prompt: str = "") -> list[dict]:
    """
    Analyse a list of jobs in batches.
    Returns list of jobs enriched with AI fields.
    Jobs that fail AI analysis keep their original data.
    """
    config = _load_config()
    ai_config = config.get("ai", {})
    min_score = ai_config.get("min_relevance_score", 0)
    rate_limit = ai_config.get("rate_limit_seconds", 7.0)
    model = ai_config.get("model", "gemini-2.5-flash")
    fetch_jd = ai_config.get("fetch_job_descriptions", True)

    resume = _load_resume()
    enriched = []
    total = len(jobs)

    # Fetch JDs upfront if enabled
    if fetch_jd:
        print(f"  [AI] Fetching job descriptions...")
        for job in jobs:
            job["_jd_text"] = fetch_description(job.get("job_url", ""))

    # Process in batches
    batches = [jobs[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    print(f"  [AI] {total} jobs → {len(batches)} API calls (batch size {BATCH_SIZE})")

    for batch_num, batch in enumerate(batches):
        print(f"  [AI] Batch {batch_num + 1}/{len(batches)} ({len(batch)} jobs)...")

        prompt = _build_batch_prompt(batch, resume, config, preference_prompt)
        results = generate(prompt, model=model, rate_limit_seconds=rate_limit)

        if not results:
            print(f"    → Batch failed, keeping jobs without AI enrichment")
            enriched.extend(batch)
            continue

        # results should be {"analyses": [...]}
        analyses = results.get("analyses", [])

        for i, job in enumerate(batch):
            ai_data = analyses[i] if i < len(analyses) else {}
            job.pop("_jd_text", None)  # clean temp field

            if ai_data:
                score = _clamp(ai_data.get("relevance_score", 0))
                if min_score > 0 and score < min_score:
                    print(f"    → Filtered: '{job.get('name', '?')[:40]}' (score: {score})")
                    continue

                enriched.append({
                    **job,
                    "ai_score": score,
                    "ai_summary": str(ai_data.get("summary", ""))[:2000],
                    "ai_match_score": _clamp(ai_data.get("match_score", 0)),
                    "ai_why_fit": str(ai_data.get("why_fit", ""))[:2000],
                    "ai_key_requirements": ai_data.get("key_requirements", []),
                    "ai_red_flags": ai_data.get("red_flags", []),
                })
            else:
                enriched.append(job)

    return enriched


def _build_batch_prompt(
    jobs: list[dict],
    resume: str,
    config: dict,
    preference_prompt: str,
) -> str:
    """Build a single prompt that analyses multiple jobs at once."""
    priorities = config.get("priorities", [])
    experience = config.get("experience_years", 0)
    preferred_locations = config.get("locations", {}).get("preferred", [])

    job_listings = []
    for i, job in enumerate(jobs):
        jd = job.get("_jd_text", "")
        entry = [
            f"Job {i + 1}:",
            f"  Title: {job.get('name', '')}",
            f"  Company: {job.get('company', '')}",
            f"  Location: {job.get('location', '')}",
            f"  Stage: {job.get('company_stage', '')}",
            f"  CTC: {job.get('ctc_range', 'Not specified')}",
            f"  Source: {job.get('source', '')}",
        ]
        if jd:
            entry.append(f"  JD (excerpt): {jd[:500]}")
        job_listings.append("\n".join(entry))

    sections = [
        "You are a job search analyst. Analyse these job listings and return a JSON object.",
        "",
        "# Job Listings to Analyse",
        "\n\n".join(job_listings),
    ]

    if resume:
        sections.extend([
            "",
            "# Candidate Resume (condensed)",
            resume,
        ])

    sections.extend([
        "",
        "# Candidate Preferences",
        f"Experience: {experience} years",
        f"Preferred locations: {', '.join(preferred_locations)}",
        f"Priorities: {', '.join(priorities)}",
    ])

    if preference_prompt:
        sections.extend(["", preference_prompt])

    n = len(jobs)
    sections.extend([
        "",
        "# Instructions",
        f"Return a JSON object with an 'analyses' array containing exactly {n} objects (one per job, in order).",
        "Each object must have:",
        '{',
        '  "analyses": [',
        '    {',
        '      "relevance_score": <0-100>,',
        '      "summary": "<2-3 sentence summary of role and company>",',
        '      "key_requirements": ["<req1>", "<req2>"],',
        '      "red_flags": ["<concern if any>"],',
        '      "match_score": <0-100, how well does the candidate match>,',
        '      "why_fit": "<1-2 sentences on why candidate fits this role>"',
        '    }',
        '  ]',
        '}',
        "",
        "Scoring: 90+=perfect, 70-89=strong, 50-69=moderate, <50=weak.",
        "Be concise. Keep summary and why_fit under 200 chars each.",
        "If no JD is available, base analysis on title+company+metadata only.",
    ])

    return "\n".join(sections)


def _clamp(value, low: int = 0, high: int = 100) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return 0
