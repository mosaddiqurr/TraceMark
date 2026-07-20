"""Optional adapter for the official Content Authenticity Initiative SDK."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ProvenanceState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    ABSENT = "absent"
    UNSUPPORTED = "unsupported"
    VERIFICATION_UNAVAILABLE = "verification_unavailable"


@dataclass(frozen=True, slots=True)
class ProvenanceResult:
    state: ProvenanceState
    manifest: Mapping[str, Any] | None = None
    detail: str | None = None


class ProvenanceAdapter(ABC):
    @abstractmethod
    def sign(self, source: Path, destination: Path, manifest: Mapping[str, Any]) -> ProvenanceResult:
        raise NotImplementedError

    @abstractmethod
    def verify(self, source: Path) -> ProvenanceResult:
        raise NotImplementedError


class C2PAProvenanceAdapter(ProvenanceAdapter):
    """Thin optional adapter; SDK/native failures never break pixel watermarking.

    Signing is enabled only when a callback and development/production certificate
    chain are explicitly supplied.  Private key material is never retained here.
    """

    def __init__(
        self,
        *,
        signing_callback: Callable[[bytes], bytes] | None = None,
        certificate_chain_pem: str | None = None,
        signing_algorithm: str = "ES256",
        timestamp_url: str | None = None,
    ) -> None:
        self._callback = signing_callback
        self._certificate_chain = certificate_chain_pem
        self._algorithm = signing_algorithm
        self._timestamp_url = timestamp_url

    @staticmethod
    def _sdk() -> Any | None:
        try:
            import c2pa  # type: ignore[import-not-found]
        except (ImportError, OSError):
            return None
        return c2pa

    def sign(self, source: Path, destination: Path, manifest: Mapping[str, Any]) -> ProvenanceResult:
        sdk = self._sdk()
        if sdk is None:
            return ProvenanceResult(ProvenanceState.UNSUPPORTED, detail="c2pa_sdk_unavailable")
        if self._callback is None or self._certificate_chain is None:
            return ProvenanceResult(ProvenanceState.UNSUPPORTED, detail="c2pa_signer_not_configured")
        try:
            algorithm = getattr(sdk.C2paSigningAlg, self._algorithm)
            with sdk.Context() as context:
                with sdk.Signer.from_callback(
                    self._callback,
                    algorithm,
                    self._certificate_chain,
                    self._timestamp_url,
                ) as signer:
                    with sdk.Builder(dict(manifest), context) as builder:
                        builder.sign_file(str(source), str(destination), signer)
        except Exception as exc:  # native SDK has platform-specific exception types
            return ProvenanceResult(
                ProvenanceState.VERIFICATION_UNAVAILABLE,
                detail=f"c2pa_sign_failed:{type(exc).__name__}",
            )
        return ProvenanceResult(ProvenanceState.VALID, manifest=dict(manifest))

    def verify(self, source: Path) -> ProvenanceResult:
        sdk = self._sdk()
        if sdk is None:
            return ProvenanceResult(ProvenanceState.UNSUPPORTED, detail="c2pa_sdk_unavailable")
        try:
            with sdk.Context() as context:
                with sdk.Reader(str(source), context=context) as reader:
                    raw = reader.detailed_json() if hasattr(reader, "detailed_json") else reader.json()
            manifest = json.loads(raw)
        except Exception as exc:
            message = str(exc).lower()
            if "manifest" in message and ("not found" in message or "no " in message):
                return ProvenanceResult(ProvenanceState.ABSENT, detail="no_c2pa_manifest")
            return ProvenanceResult(
                ProvenanceState.VERIFICATION_UNAVAILABLE,
                detail=f"c2pa_verify_failed:{type(exc).__name__}",
            )
        state_text = str(manifest.get("validation_state", "")).lower()
        state = ProvenanceState.VALID if state_text in {"valid", "trusted"} else ProvenanceState.INVALID
        return ProvenanceResult(state, manifest=manifest)

