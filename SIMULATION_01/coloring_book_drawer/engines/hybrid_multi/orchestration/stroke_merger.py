"""
Stroke Merger
================
Merges per-region reveal masks into a globally ordered sequence using
region-type priority rules defined in :class:`PreferenceRules`.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

from ..config import RegionType
from ..classification.classifier import RegionInfo
from ..assignment.preference_rules import PreferenceRules

logger = logging.getLogger(__name__)


class StrokeMerger:
    """Orders and merges region reveals according to priority rules.

    Regions are sorted by their :pyattr:`RegionType` priority so that
    visually important areas (e.g. *FOCAL*, *EDGE*) appear before
    background fills and highlights.  Within the same priority level,
    regions are sub-sorted by area (larger regions first) to ensure a
    stable, visually pleasing reveal order.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def get_ordered_regions(regions: List[RegionInfo]) -> List[RegionInfo]:
        """Return *regions* sorted by :class:`PreferenceRules` priority.

        Parameters
        ----------
        regions : List[RegionInfo]
            Unordered list of classified regions.

        Returns
        -------
        List[RegionInfo]
            A new list sorted ascending by priority value (lower =
            earlier in the reveal sequence).  Ties are broken by
            descending area so larger regions of the same type are
            revealed first.
        """
        if not regions:
            return []

        try:
            return sorted(
                regions,
                key=lambda r: (
                    PreferenceRules.get_priority(r.region_type),
                    -r.area,  # larger regions first within same priority
                ),
            )
        except Exception:
            logger.exception(
                "Failed to sort regions by priority; returning original order."
            )
            return list(regions)

    @staticmethod
    def merge_reveal_sequence(
        region_reveals: Dict[int, np.ndarray],
        regions: List[RegionInfo],
    ) -> List[Tuple[int, np.ndarray]]:
        """Merge reveal masks into a priority-ordered sequence.

        Parameters
        ----------
        region_reveals : dict
            Mapping ``region_id → reveal_mask`` (float ``(H, W)`` arrays
            with values in ``[0, 1]``).
        regions : List[RegionInfo]
            The full list of classified regions (used for ordering).

        Returns
        -------
        List[Tuple[int, np.ndarray]]
            Ordered list of ``(region_id, reveal_mask)`` tuples.  The
            order respects :class:`PreferenceRules` priority.  Regions
            present in *regions* but missing from *region_reveals* are
            skipped with a warning.
        """
        ordered_regions = StrokeMerger.get_ordered_regions(regions)
        sequence: List[Tuple[int, np.ndarray]] = []

        for region in ordered_regions:
            rid = region.region_id
            mask = region_reveals.get(rid)
            if mask is None:
                logger.warning(
                    "Region %d (type=%s) has no reveal mask; skipping.",
                    rid,
                    region.region_type.value,
                )
                continue
            sequence.append((rid, mask))

        logger.debug(
            "Merged reveal sequence: %d regions ordered by priority.",
            len(sequence),
        )
        return sequence
