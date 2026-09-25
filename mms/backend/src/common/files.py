"""File upload helpers (style images, sample attachments) — migration-safe.

Uses `django.utils.deconstruct.deconstructible` so the upload target keeps a
deterministic migration path; filenames stay unique (uuid) at runtime.
"""

import os
import uuid

from django.utils.deconstruct import deconstructible


@deconstructible
class UploadToPath:
    def __init__(self, subdir: str):
        self.subdir = subdir

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f"{self.subdir}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, UploadToPath) and other.subdir == self.subdir


def media_upload_to(subdir: str):
    return UploadToPath(subdir)