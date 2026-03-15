"""
Relevance filter for job titles.
Now config-driven (reads from config.yaml) with hardcoded fallback.
AI scoring happens downstream in ai/pipeline.py — this is the fast pre-filter.
"""
import yaml
from pathlib import Path

_config = None


def _load_config() -> dict:
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            try:
                _config = yaml.safe_load(config_path.read_text())
            except Exception:
                _config = {}
        else:
            _config = {}
    return _config


def _get_required_keywords() -> list[str]:
    config = _load_config()
    return config.get("roles", {}).get("required_keywords", [
        "chief of staff",
        "chief-of-staff",
        "founder's office",
        "founder office",
        "founders office",
        "head of staff",
    ])


def _get_blocked_keywords() -> list[str]:
    config = _load_config()
    return config.get("roles", {}).get("blocked_keywords", [
        "intern", "co-founder", "co founder", "cofounder",
        "executive assistant", "analyst", "fresher", "entry level",
        "volunteer", "freelance", "part-time", "part time",
        "equity only", "equity based", "student", "mba intern",
    ])


def is_relevant(title: str) -> bool:
    """
    Returns True only if the title matches required keywords
    and doesn't match blocked keywords. Config-driven with fallback.
    """
    t = title.lower().strip()

    required = _get_required_keywords()
    if not any(kw in t for kw in required):
        return False

    blocked = _get_blocked_keywords()
    if any(kw in t for kw in blocked):
        return False

    return True


def classify_position(title: str) -> str:
    """Classify a job title into a position category using config rules."""
    config = _load_config()
    t = title.lower()

    position_rules = config.get("roles", {}).get("position_rules", [])
    for rule in position_rules:
        if any(kw in t for kw in rule.get("match", [])):
            return rule.get("label", "Other")

    # Fallback if no config
    if any(k in t for k in ["founder's office", "founder office", "founders office"]):
        return "Founder's Office"
    return "Chief of Staff"
