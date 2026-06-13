"""Interview-prep brief — validation + rendering.

Given a scored Job + the user's profile, produces a focused brief:
likely behavioural questions, role-specific technical/case questions,
watch-outs, questions to ask the interviewer.

Claude Code writes the company-specific content in-conversation and
passes it via ``--content``; a templated fallback exists otherwise (the
fallback is honest about its limitations — generic questions only).
"""

from danapply.interview.prep import (
    InterviewBrief,
    brief_from_content,
    build_interview_brief,
    render_brief_markdown,
)

__all__ = [
    "InterviewBrief",
    "brief_from_content",
    "build_interview_brief",
    "render_brief_markdown",
]
