"""
Fetch job descriptions from URLs.
Extracts clean text from job listing pages for AI analysis.
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

# Tags that typically contain job description content
JD_SELECTORS = [
    "[class*='description']",
    "[class*='job-detail']",
    "[class*='job_detail']",
    "[class*='jobDescription']",
    "[class*='posting-description']",
    "[id*='description']",
    "[id*='job-detail']",
    "article",
    "[role='main']",
    ".content-body",
    ".job-content",
]

# Max characters to extract (keeps token usage low)
MAX_CHARS = 3000


def fetch_description(url: str) -> str:
    """
    Fetch and extract job description text from a URL.
    Returns empty string on failure (graceful degradation).
    """
    if not url:
        return ""

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove noise
        for tag in soup.select("script, style, nav, header, footer, iframe"):
            tag.decompose()

        # Try targeted selectors first
        for selector in JD_SELECTORS:
            elements = soup.select(selector)
            if elements:
                text = " ".join(el.get_text(separator=" ", strip=True) for el in elements)
                if len(text) > 100:
                    return _clean(text)

        # Fallback: grab body text
        body = soup.find("body")
        if body:
            text = body.get_text(separator=" ", strip=True)
            if len(text) > 100:
                return _clean(text)

        return ""

    except Exception:
        return ""


def _clean(text: str) -> str:
    """Collapse whitespace, truncate to MAX_CHARS."""
    cleaned = " ".join(text.split())
    return cleaned[:MAX_CHARS]
