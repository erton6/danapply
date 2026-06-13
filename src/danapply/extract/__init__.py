"""LLM-powered extraction & refinement helpers.

These modules wrap the Anthropic API to upgrade ``Job`` records produced by
heuristic parsers. The pattern is always:

  1. Cheap heuristic parser produces a ``Job`` with whatever it can read
     (``data_confidence`` set honestly).
  2. If the user opts in (``--boost`` flag) and the parse is medium/low
     confidence, the extract module re-runs the same input through an LLM
     and produces a high-confidence ``Job``.

The extract modules NEVER raise on bad API responses — they fall back to
returning the original Job unchanged and log the issue. The heuristic
result is always the safety net.
"""
