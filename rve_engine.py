"""
Kinepool // KUTS Revision 8 Resource-Verification Engine (RVE), Engine C.

IMPORTANT - what a signature here means:
The HMAC proves that THIS server received and recorded exactly this packet at
this time. It does NOT prove the readings are true. Until a real metering
source (smart-meter API, cloud billing API, ...) is integrated, packets carry
metering_source = "SELF_REPORTED" and trust_level = "UNVERIFIED".

Double-counting is prevented in the database (unique idempotency_key per
terminal and unique source_reading_id), not in process memory.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

log = logging.getLogger("kinepool.rve")


def load_signing_key() -> bytes:
    key = os.getenv("RVE_SIGNING_KEY")
    if key:
        return key.encode("utf-8")
    log.warning("RVE_SIGNING_KEY not set: using an ephemeral key. Signatures made before "
                "the next restart will NOT verify afterwards. Set RVE_SIGNING_KEY in production.")
    return secrets.token_bytes(32)


class ResourceVerificationEngine:
    SELF_REPORTED = "SELF_REPORTED"

    def __init__(self, signing_key: bytes):
        if len(signing_key) < 16:
            raise ValueError("RVE signing key too short.")
        self._key = signing_key

    @staticmethod
    def new_measurement_id() -> str:
        return hashlib.sha256(uuid.uuid4().bytes + secrets.token_bytes(16)).hexdigest()

    def _sign(self, packet: dict) -> str:
        body = {k: v for k, v in packet.items() if k != "rve_signature"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hmac.new(self._key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def attest_telemetry(self, node_id: str, terminal_uid: str, category_code: int,
                         resource_type: str, raw_metrics: dict,
                         metering_source: str = SELF_REPORTED) -> dict:
        packet = {
            "measurement_id": self.new_measurement_id(),
            "node_id": node_id,
            "terminal_uid": terminal_uid,
            "category_code": f"{category_code:02d}",
            "resource_type": resource_type,
            "metering_source": metering_source,
            "trust_level": "UNVERIFIED" if metering_source == self.SELF_REPORTED else "METERED",
            "raw_metrics": raw_metrics,
            "attested_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ATTESTED",
        }
        packet["rve_signature"] = self._sign(packet)
        return packet

    def verify_packet(self, packet: dict) -> bool:
        sig = packet.get("rve_signature", "")
        return hmac.compare_digest(sig, self._sign(packet))