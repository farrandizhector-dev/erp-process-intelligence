"""Automation opportunity scoring for P2P activities.

Implements the composite scoring model from CONTEXT.md Section 9.5.
"""

from __future__ import annotations

import logging
from math import log2

logger = logging.getLogger(__name__)

# TODO: implement in Phase 4


def shannon_entropy(distribution: dict[str, int]) -> float:
    """Compute normalized Shannon entropy of a frequency distribution.

    Returns 0 for single-value distributions, 1 for uniform distributions.

    Args:
        distribution: Mapping of category → count.

    Returns:
        Normalized entropy in [0, 1].
    """
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    probs = [count / total for count in distribution.values() if count > 0]
    if len(probs) <= 1:
        return 0.0
    raw_entropy = -sum(p * log2(p) for p in probs)
    max_entropy = log2(len(probs))
    return raw_entropy / max_entropy if max_entropy > 0 else 0.0
