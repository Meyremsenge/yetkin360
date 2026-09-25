"""
Visibility filtering logic for public profile access.

Implements rules for filtering public (visibility='PUBLIC') talent profiles
and their associated verified experiences.

Pure calculation functions — no database dependency. Used by public endpoint
and other visibility-aware features.
"""

from app.models import VerifiedExperience


def filter_public_experiences(
    experiences: list[VerifiedExperience],
) -> list[VerifiedExperience]:
    """
    Filter VerifiedExperience list to only PUBLIC visibility records.

    Args:
        experiences: List of VerifiedExperience objects

    Returns:
        List of VerifiedExperience objects with visibility='PUBLIC' only

    Implements AC-5 (AC-S3): granular visibility filtering at experience level
    """
    return [exp for exp in experiences if exp.visibility == "PUBLIC"]
