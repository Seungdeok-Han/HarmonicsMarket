"""Safe upload helpers for marketplace and community media."""
from __future__ import annotations

import os
import uuid
from typing import Iterable, List, Optional

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.avi', '.wmv', '.webm', '.mkv'}
ALLOWED_EXT = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT


def uploads_dir() -> str:
    path = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(path, exist_ok=True)
    return path


def media_type_for(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return 'video' if ext in ALLOWED_VIDEO_EXT else 'image'


def save_upload(file: FileStorage, *, allowed: Optional[set] = None) -> Optional[str]:
    """Save one file with a collision-safe name. Returns stored filename or None."""
    if not file or not getattr(file, 'filename', None):
        return None
    original = secure_filename(file.filename)
    if not original:
        return None
    ext = os.path.splitext(original)[1].lower()
    allowed = allowed or ALLOWED_EXT
    if ext not in allowed:
        return None
    stored = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(uploads_dir(), stored))
    return stored


def save_uploads(files: Iterable[FileStorage], *, allowed: Optional[set] = None) -> List[str]:
    names: List[str] = []
    for f in files:
        name = save_upload(f, allowed=allowed)
        if name:
            names.append(name)
    return names


def delete_upload(filename: str) -> None:
    if not filename:
        return
    # Prevent path traversal
    safe = os.path.basename(filename)
    path = os.path.join(uploads_dir(), safe)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
