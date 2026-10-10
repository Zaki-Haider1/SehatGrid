"""Compatibility imports for the original workflow module.

New backend code should import from the focused service modules directly. This
module keeps the names used by the current API and tests stable during T00.
"""

from .optimization.allocation import optimize
from .services.capacity import capacity_upsert
from .services.eligibility import recommendations
from .services.plans import approve
from .services.referrals import require, reserve, transition

__all__ = [
    "approve",
    "capacity_upsert",
    "optimize",
    "recommendations",
    "require",
    "reserve",
    "transition",
]
