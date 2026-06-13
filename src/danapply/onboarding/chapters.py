"""The 10 onboarding chapters, defined declaratively.

Source-of-truth for what gets asked. The runner walks this list; the
profile_builder translates the answers into yaml files.

Order matters. Branching is light (no real conditional questions in v0.0.8
beyond the dagpenge ``on_dagpenge`` boolean gating Chapter 7's follow-ups).
"""

from __future__ import annotations

from danapply.onboarding.models import Chapter, Question


def _q(qid: str, prompt: str, **kwargs) -> Question:
    return Question(id=qid, prompt=prompt, **kwargs)


CHAPTERS: list[Chapter] = [
    # -----------------------------------------------------------------------
    Chapter(
        id="welcome",
        title="Welcome",
        intent="Set expectations and let the user opt out before answering anything.",
        pre_amble=(
            "Hi, I'm DanApply.\n\n"
            "Before we start: I'm going to ask you about your background, what "
            "kind of job you're looking for, and what's not working in your "
            "search so far. It takes about 30–45 min. Nothing leaves your "
            "machine — everything stays in ~/danapply-data/.\n\n"
            "You can pause whenever — your progress is saved after each "
            "chapter. Run `danapply onboard --resume` to come back."
        ),
        questions=[
            _q("ready", "Ready to start?", answer_type="bool", default=True),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="situation",
        title="Where you stand right now",
        intent="Ground in present reality; calibrate emotional state.",
        questions=[
            _q("name", "What's your full name (as you want it on your CV)?"),
            _q(
                "employment_status",
                "What's your situation right now?",
                answer_type="choice",
                choices=[
                    "employed",
                    "unemployed",
                    "between roles",
                    "on dagpenge",
                    "student",
                    "other",
                ],
            ),
            _q(
                "search_duration_months",
                "How long have you been actively looking (in months)?",
                answer_type="number",
                default=0,
            ),
            _q(
                "stress_level",
                "How stressed are you about the search, 1 (calm) to 5 (very stressed)?",
                answer_type="number",
                default=3,
            ),
            _q(
                "location_city",
                "Which Danish city are you based in (or moving to)?",
                default="",
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="story",
        title="Your story so far",
        intent="Career history + the why behind each step. Surfaces voice.",
        pre_amble=(
            "Walk me through your last few roles + your education at a high "
            "level. I'll fill in the structured CV later — this is for context."
        ),
        questions=[
            _q(
                "career_summary",
                "In 2–4 sentences, walk me through what you've done so far:",
                answer_type="long_text",
            ),
            _q(
                "proudest_achievement",
                "What's something you're proud of — paid or unpaid? "
                "(One sentence is fine.)",
                answer_type="long_text",
            ),
            _q(
                "best_energy_source",
                "What kind of work makes you lose track of time?",
            ),
            _q(
                "biggest_drain",
                "What kind of work drains you, even when you're good at it?",
                required=False,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="targets",
        title="What you're aiming for",
        intent="Target roles + geo + arrangement. Scoring rubric feeds from here.",
        questions=[
            _q(
                "tier_a_titles",
                "Name 2–5 job titles you'd actively apply to "
                "(comma-separated, e.g. 'Business Analyst, Insights Analyst'):",
            ),
            _q(
                "tier_b_titles",
                "Any adjacent titles you'd take seriously? (Optional, comma-separated)",
                required=False,
            ),
            _q(
                "geography_primary",
                "Primary geography? (e.g. 'Copenhagen' or 'Aarhus, Copenhagen')",
                default="",
            ),
            _q(
                "arrangement",
                "Work arrangement preference?",
                answer_type="choice",
                choices=["office", "hybrid", "remote"],
                default="hybrid",
            ),
            _q(
                "remote_ok",
                "Open to fully-remote DK roles?",
                answer_type="bool",
                default=True,
            ),
            _q(
                "salary_floor_dkk",
                "Salary floor in DKK/month (before tax). Type 0 to skip.",
                answer_type="number",
                default=0,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="constraints",
        title="Constraints and red lines",
        intent="Filters that auto-deduct from scoring + visa/language admin.",
        questions=[
            _q(
                "visa_status",
                "Visa status?",
                answer_type="choice",
                choices=[
                    "eu_eea",
                    "permanent_residence",
                    "work_permit",
                    "needs_sponsorship",
                ],
            ),
            _q(
                "danish_level",
                "Your Danish level (CEFR)?",
                answer_type="choice",
                choices=["none", "A1", "A2", "B1", "B2", "C1", "native"],
                default="B1",
            ),
            _q(
                "english_level",
                "Your English level?",
                answer_type="choice",
                choices=["intermediate", "advanced", "fluent", "native"],
                default="fluent",
            ),
            _q(
                "excluded_industries",
                "Industries you'd refuse outright? (Comma-separated; e.g. "
                "'tobacco, gambling, fossil_fuels'.) Empty to skip.",
                required=False,
            ),
            _q(
                "max_commute_minutes",
                "Maximum one-way commute in minutes (0 to skip):",
                answer_type="number",
                default=0,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="self_assessment",
        title="Honest self-assessment",
        intent="Distinguish trained-in from actually-good-at.",
        pre_amble=(
            "Take a beat with these. The honest version, not the LinkedIn version."
        ),
        questions=[
            _q(
                "real_strengths",
                "What are you actually good at? (Comma-separated phrases.)",
            ),
            _q(
                "cv_overstated",
                "What's something on your CV that's not as strong as it sounds? "
                "(Optional — empty to skip.)",
                required=False,
            ),
            _q(
                "cv_undersold",
                "What's something you're good at that isn't on your CV yet? "
                "(Optional.)",
                required=False,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="reality_check",
        title="Reality-check synthesis",
        intent="Show the user what was heard; let them confirm or correct.",
        pre_amble=(
            "I'll print a summary of what you've told me. You'll get a chance "
            "to confirm before anything is saved as profile.yaml. If something "
            "looks wrong, type 'no' and we'll restart the whole interview "
            "(your previous state is kept for `--resume`)."
        ),
        questions=[
            _q(
                "confirm",
                "Does the summary above look right?",
                answer_type="bool",
                default=True,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="dk_admin",
        title="DK admin (dagpenge, deadlines)",
        intent="dagpenge.yaml + other deadlines so trackers work later.",
        questions=[
            _q(
                "on_dagpenge",
                "Are you on dagpenge right now?",
                answer_type="bool",
                default=False,
            ),
            _q(
                "a_kasse",
                "If on dagpenge: which a-kasse? (Leave blank otherwise.)",
                required=False,
            ),
            _q(
                "my_plan_field",
                "If on dagpenge: what's on your My Plan (Min Plan)? "
                "(Leave blank otherwise.)",
                required=False,
            ),
            _q(
                "weekly_threshold",
                "Weekly application requirement (typically 2). Type 0 to skip.",
                answer_type="number",
                default=2,
            ),
        ],
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="existing_cv",
        title="Your existing CV",
        intent="Capture (and gently calibrate) the user's current CV content.",
        pre_amble=(
            "If you have an existing CV in markdown / text form, point me at "
            "the file. I'll save it as cv_content.md and run a Danish-mode "
            "register check. Skip with empty input — you can always run "
            "`danapply tailor` later without this."
        ),
        questions=[
            _q(
                "cv_sample_path",
                "Path to your existing CV (text / markdown). Leave blank to skip:",
                answer_type="file_path",
                required=False,
            ),
        ],
        optional=True,
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="voice_exercise",
        title="The voice exercise",
        intent="Capture the user's writing voice from a sample.",
        pre_amble=(
            "This is the moat. Point me at a writing sample you wrote "
            "yourself — a cover letter draft, a blog post, journal entries. "
            "500+ words ideal. DanApply uses it to make every generated "
            "cover letter sound like you instead of a template. Skip to come "
            "back later with `danapply voice capture <file>`."
        ),
        questions=[
            _q(
                "voice_sample_path",
                "Path to your writing sample. Leave blank to skip:",
                answer_type="file_path",
                required=False,
            ),
        ],
        optional=True,
    ),
    # -----------------------------------------------------------------------
    Chapter(
        id="wrap_up",
        title="Wrap-up",
        intent="Confirm, show what got saved, set expectations.",
        post_amble=(
            "All set. Next step: drop some job listings into "
            "~/danapply-data/raw_searches/ (PDF, text, or .eml) and run "
            "`danapply parse --batch` + `danapply score` + `danapply tailor`. "
            "Pasted text works too: `danapply parse --paste \"...\"`."
        ),
        questions=[],
    ),
]


def get_chapter(chapter_id: str) -> Chapter | None:
    for c in CHAPTERS:
        if c.id == chapter_id:
            return c
    return None


def chapter_index(chapter_id: str) -> int:
    """0-based position of a chapter in the canonical order. -1 if unknown."""
    for i, c in enumerate(CHAPTERS):
        if c.id == chapter_id:
            return i
    return -1
