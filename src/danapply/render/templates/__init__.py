"""CV / cover-letter visual templates.

Currently only ``canonical`` is implemented. Adding a template means creating
a new module here that exposes ``build_cv_pdf(job_data, output_path, profile)``
and ``build_cover_letter_pdf(data, output_path, profile)``.
"""

from danapply.render.templates import canonical

__all__ = ["canonical"]
