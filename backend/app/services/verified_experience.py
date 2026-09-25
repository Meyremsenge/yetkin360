"""
VerifiedExperience service: token generation for public verification links.

Implements YET-106 (public-dogrulama-linki), AC-4 (AC-S1).
"""

import secrets


def generate_public_token() -> str:
    """
    Generate a cryptographically secure random token for public verification link.

    Uses secrets.token_urlsafe() with 32 bytes (256 bits) entropy.
    This exceeds AC-S1 minimum requirement of ≥128 bits.

    Alphabet: base64url (64 chars)
    Length: typically 43-44 characters (encoding 32 bytes)
    Entropy: 256 bits >> 128 bits minimum (AC-S1)

    Usage:
        VerifiedExperience.public_token üretiminde kullanılacak (T8 attestation transition).
        NOTE: Bu fonksiyon şu an YERINDEkalmış — token üretimi T8 transition'a entegre etme
              ayrı bir görev (YET-???).

    Returns:
        str: Randomly generated token suitable for URL-safe use
    """
    return secrets.token_urlsafe(32)
