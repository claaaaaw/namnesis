"""
Namnesis Cryptographic Primitives.

Signing only — no client-side encryption.  Data confidentiality is
handled by access control (Relay NFT-gate + presigned URLs).

Provides:
- ECDSA/secp256k1 manifest signing (EIP-191)
- RFC 8785 JSON Canonicalization for deterministic signing payloads
- SHA-256 blob ID computation
"""

from __future__ import annotations

import copy
from typing import Any

import rfc8785

from ..utils import sha256_hex


class CryptoError(ValueError):
    pass


class SignatureError(CryptoError):
    pass


def blob_id(data: bytes) -> str:
    """Compute blob ID as SHA-256 hex digest of raw data."""
    return sha256_hex(data)


def canonicalize_manifest_for_signing(manifest: dict[str, Any]) -> bytes:
    """Canonicalize manifest (without signature) using RFC 8785 JCS."""
    payload = copy.deepcopy(manifest)
    payload.pop("signature", None)
    return rfc8785.dumps(payload)


def sign_manifest(manifest: dict[str, Any], private_key_hex: str) -> dict[str, str]:
    """Sign manifest with ECDSA/secp256k1 (EIP-191 personal_sign).

    Args:
        manifest: The manifest dict (without final signature).
        private_key_hex: 0x-prefixed hex ECDSA private key.

    Returns:
        Signature object to embed into the manifest.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct

    canonical_bytes = canonicalize_manifest_for_signing(manifest)
    account = Account.from_key(private_key_hex)
    signable = encode_defunct(primitive=canonical_bytes)
    signed = account.sign_message(signable)
    return {
        "alg": "ecdsa_secp256k1_eip191",
        "payload_alg": "rfc8785_jcs_without_signature_utf8",
        "signer_address": account.address,
        "sig": signed.signature.hex(),
    }


def verify_manifest_signature(
    manifest: dict[str, Any],
    trusted_addresses: set[str],
) -> None:
    """Verify manifest ECDSA signature against a set of trusted addresses.

    Args:
        manifest: The full manifest dict including ``signature``.
        trusted_addresses: Set of trusted Ethereum addresses (checksummed or lower).

    Raises:
        SignatureError: If verification fails.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct

    signature = manifest.get("signature")
    if not isinstance(signature, dict):
        raise SignatureError("Manifest missing signature object.")

    sig_hex = signature.get("sig")
    signer_address = signature.get("signer_address")
    if not sig_hex or not signer_address:
        raise SignatureError("Manifest signature is incomplete.")

    trusted_lower = {a.lower() for a in trusted_addresses}
    if signer_address.lower() not in trusted_lower:
        raise SignatureError("Signer is not trusted.")

    canonical_bytes = canonicalize_manifest_for_signing(manifest)
    signable = encode_defunct(primitive=canonical_bytes)
    try:
        recovered = Account.recover_message(signable, signature=bytes.fromhex(sig_hex.removeprefix("0x")))
    except Exception as exc:
        raise SignatureError("Invalid manifest signature.") from exc

    if recovered.lower() != signer_address.lower():
        raise SignatureError("Recovered signer does not match declared signer_address.")
