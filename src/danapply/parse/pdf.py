"""PDF parser.

Extracts text via pypdf, then infers core fields (title, company, location,
posting date, language) using a combination of filename heuristics and
text-content patterns.

This is a deliberately simple baseline. v0.0.3 will add LLM-based field
extraction for higher accuracy on messy PDFs. For now we mark
``data_confidence`` honestly so downstream workflows know what they're
getting.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from danapply.models import DataConfidence, Job

# ---------------------------------------------------------------------------
# Filename heuristics — most user-saved job PDFs have informative names.
# ---------------------------------------------------------------------------

# Common separators used by browsers and job boards
_FILENAME_SPLITTERS = [" - ", " _ ", " | ", " — ", " – "]

# Sites whose "Save as PDF" output is recognisable. Order matters — more
# specific patterns first. We require domain-like matches to avoid grabbing
# "linkedin" from share-button URLs on unrelated company pages.
_KNOWN_SOURCE_HINTS: tuple[tuple[str, str], ...] = (
    ("linkedin.com/jobs", "linkedin"),
    ("linkedin.com/in/", "linkedin"),
    ("jobindex.dk",       "jobindex"),
    ("thehub.io",         "thehub"),
    ("indeed.com",        "indeed"),
    ("indeed.dk",         "indeed"),
    ("glassdoor.com",     "glassdoor"),
    ("glassdoor.dk",      "glassdoor"),
    ("greenhouse.io",     "greenhouse"),
    ("jobs.lever.co",     "lever"),
    ("teamtailor.com",    "teamtailor"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("workable.com",      "workable"),
    ("hr-on.com",         "hr-on"),
    ("bamboohr.com",      "bamboohr"),
    ("salesforce-sites.com", "salesforce-sites"),
    ("salesforcesites",   "salesforce-sites"),
    ("eures.europa.eu",   "eures"),
    ("mckinsey.com",      "mckinsey"),
)

# Generic filename hints used only when no domain matches — much lower
# confidence than a real URL pattern.
_FILENAME_FALLBACK_HINTS: tuple[tuple[str, str], ...] = (
    ("linkedin", "linkedin"),
    ("jobindex", "jobindex"),
    ("thehub",   "thehub"),
)


# Filename suffixes that aren't useful as title or company (drop them so we
# don't end up with "title=Business Analyst, company=LinkedIn").
_FILENAME_SOURCE_SUFFIXES = {
    "linkedin", "smartrecruiters", "the hub", "thehub", "jobindex",
    "glassdoor", "indeed", "wellfound", "google jobs", "job details",
    "career page", "careers", "stillingsopslag", "jobannonce",
}


def _split_filename(stem: str) -> list[str]:
    """Break ``stem`` on common separators into clean, useful tokens.

    Known source-name suffixes (LinkedIn, SmartRecruiters, etc.) are stripped
    so they don't get mistaken for company names.
    """
    parts = [stem]
    for sep in _FILENAME_SPLITTERS:
        new_parts: list[str] = []
        for p in parts:
            new_parts.extend(p.split(sep))
        parts = new_parts
    cleaned: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.lower() in _FILENAME_SOURCE_SUFFIXES:
            continue
        cleaned.append(p)
    return cleaned


def _guess_source_from_text(text: str, filename: str) -> str:
    """Pattern-match the page footer / URL line / filename for a source name.

    Domain-level patterns in the page text win over generic filename hints —
    avoids false positives like grabbing 'linkedin' from a share-button URL
    on an unrelated company's career page.
    """
    text_lower = text[:4000].lower()
    for needle, source in _KNOWN_SOURCE_HINTS:
        if needle in text_lower:
            return source

    filename_lower = filename.lower()
    for needle, source in _FILENAME_FALLBACK_HINTS:
        if needle in filename_lower:
            return source

    return f"pdf:{filename}"


def _guess_language(text: str) -> str:
    """Very simple language detection by language-unique-marker counting.

    Returns one of EN, DA, DE, HU. Markers are restricted to forms that
    contain language-specific characters (æ, ø, å, ü, ö, é, ő, ű, etc.)
    or words that don't collide with English. Generic stopwords like " a "
    are excluded because they appear in URLs and English contractions.
    """
    if not text:
        return "EN"

    sample = text[:5000].lower()

    da_markers = (
        " ikke ", " jeg ", " være ", " søger ", " ansøgning", " stilling",
        " virksomhed", "ansøgningsfrist", " fristen ", " kollega",
        "stillingen", "ansøg",
    )
    de_markers = (
        " bewerbung", " stelle", "stellenangebot", " mitarbeiter",
        " wir suchen", " arbeitgeber", " für ", " müssen", " können",
        " größe", " büro",
    )
    hu_markers = (
        " és ", " hogy ", " állás", " állás ", " munkahely", " fizetés",
        " jelentkez", " feladat", " vállalat", "ünk ", " ők ", "ség",
    )

    da_count = sum(sample.count(m) for m in da_markers)
    de_count = sum(sample.count(m) for m in de_markers)
    hu_count = sum(sample.count(m) for m in hu_markers)

    counts = {"DA": da_count, "DE": de_count, "HU": hu_count}
    top_lang, top_count = max(counts.items(), key=lambda kv: kv[1])
    return top_lang if top_count >= 3 else "EN"


def _guess_title_and_company(
    text: str,
    filename_stem: str,
) -> tuple[str, str, DataConfidence]:
    """Extract title + company. Returns (title, company, confidence)."""
    filename_parts = _split_filename(filename_stem)
    text_lines = [
        line.strip()
        for line in text.split("\n")[:30]
        if line.strip()
    ]

    title = ""
    company = ""
    confidence: DataConfidence = "low"

    # ---- Strategy 1: filename like "Title - Company"
    # Examples that work:
    #   "Business Analyst - McKinsey & Company"
    #   "Sustainability Data Analyst _ Job Details"  (drops generic "Job Details")
    #   "Strategy Consultant — Implement Consulting Group"
    if len(filename_parts) >= 2:
        first, second = filename_parts[0], filename_parts[1]
        first_is_title_like = _looks_like_role_title(first)
        second_is_title_like = _looks_like_role_title(second)
        second_is_generic = second.lower() in {
            "job details", "linkedin", "careers", "job description",
            "stillingsopslag", "jobannonce", "linkedin com",
        }

        if first_is_title_like and second_is_generic:
            title = first
            confidence = "medium"
        elif first_is_title_like and not second_is_title_like:
            # "Title - Company"
            title = first
            company = second
            confidence = "high"
        elif second_is_title_like and not first_is_title_like:
            # "Company - Title"
            company = first
            title = second
            confidence = "high"
        else:
            title = first
            company = second
            confidence = "medium"

    # ---- Strategy 2: text content scan
    if not title:
        for line in text_lines:
            if _looks_like_role_title(line):
                title = line
                confidence = "medium"
                break

    # Strip generic "Job Details:" / "Stillingsopslag:" / "Position:" prefixes
    if title:
        for prefix in ("Job Details:", "Job Title:", "Position:", "Role:",
                       "Stillingsopslag:", "Jobannonce:"):
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):].strip()
                break

    if not company:
        # Common patterns: "at [Company]", "[Company] is hiring", "About [Company]"
        for line in text_lines:
            m = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.\- ]+?)(?:\s+in\s|\s*[·•|]|\s*$)",
                          line)
            if m:
                company = m.group(1).strip()
                break

    # If still nothing, take the longest filename part as a best-effort
    if not title and filename_parts:
        title = filename_parts[0]
        confidence = "low"

    return title, company, confidence


def _looks_like_role_title(text: str) -> bool:
    """Heuristic: does this look like a job title?"""
    if not text:
        return False
    if len(text) > 80 or len(text) < 3:
        return False
    role_keywords = (
        "analyst", "consultant", "engineer", "manager", "specialist",
        "advisor", "associate", "developer", "researcher", "scientist",
        "officer", "lead", "head of", "director", "coordinator", "intern",
        "graduate", "trainee", "controller", "designer", "strategist",
    )
    lowered = text.lower()
    return any(kw in lowered for kw in role_keywords)


def _guess_location(text: str) -> str | None:
    """Find a Danish-region-aware location in the first 50 lines."""
    dk_cities = (
        "Copenhagen", "København", "Aarhus", "Århus", "Odense", "Aalborg",
        "Esbjerg", "Randers", "Kolding", "Horsens", "Vejle", "Roskilde",
        "Herning", "Silkeborg", "Næstved", "Fredericia", "Viborg", "Lystrup",
        "Skødstrup", "Hellerup", "Birkerød",
    )
    for line in text.split("\n")[:50]:
        for city in dk_cities:
            if city in line:
                # Return the line as-is (often "City, Country" or just city)
                # Trim trailing garbage
                cleaned = re.sub(r"\s+", " ", line).strip()
                # Cap length so we don't take a whole paragraph
                return cleaned[:80] if len(cleaned) < 200 else city
    return None


def _guess_posting_date(text: str) -> date | None:
    """Find a YYYY-MM-DD or DD.MM.YYYY date in the first 100 lines."""
    head = "\n".join(text.split("\n")[:100])

    # YYYY-MM-DD
    m = re.search(r"\b(20\d\d)-(0\d|1[0-2])-([0-2]\d|3[01])\b", head)
    if m:
        try:
            return date.fromisoformat(m.group(0))
        except ValueError:
            pass

    # DD.MM.YYYY
    m = re.search(r"\b([0-2]\d|3[01])\.(0\d|1[0-2])\.(20\d\d)\b", head)
    if m:
        try:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mth, d)
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def parse_pdf(path: Path) -> Job:
    """Extract a Job from a PDF file. Never raises on parse failure —
    returns a low-confidence Job with whatever could be salvaged."""
    reader = PdfReader(str(path))
    text_chunks: list[str] = []
    for page in reader.pages:
        try:
            text_chunks.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — pypdf raises diverse things
            continue
    text = "\n".join(text_chunks)

    filename_stem = path.stem
    title, company, conf = _guess_title_and_company(text, filename_stem)
    location = _guess_location(text)
    posting_date = _guess_posting_date(text)
    language = _guess_language(text)
    source = _guess_source_from_text(text, path.name)

    # Best-effort URL extraction
    url = None
    m = re.search(r"https?://[^\s)>\]]+", text[:5000])
    if m:
        url = m.group(0).rstrip(",.;)")

    return Job(
        title=title,
        company=company,
        location=location,
        posting_date=posting_date,
        source=source,
        url=url,
        language=language,  # type: ignore[arg-type]
        description_raw=text,
        data_confidence=conf,
    )
