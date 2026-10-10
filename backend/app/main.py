"""The scope-v1 API replaces all unscoped legacy demo endpoints."""

from .mvp.api import app

__all__ = ["app"]
