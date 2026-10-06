"""

import hashlib
import json

GENESIS_HASH = "0" * 64
HASHED_FIELDS = ("seq", "composite_kuts_id", "measurement_id", "rve_signature",
                 "raw_kines_e8", "valuation_usd_e8", "pfs_e8", "rsp_e8", "net_e8")


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def entry_hash(prev_hash: str, fields: dict) -> str:
    payload = {k: fields[k] for k in HASHED_FIELDS}
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()


def verify_chain(entries: list) -> dict:
    """entries: dicts ordered by seq ascending, each with HASHED_FIELDS + prev_hash + entry_hash."""
    prev = GENESIS_HASH
    expected_seq = 1
    for e in entries:
        if e["seq"] != expected_seq:
            return {"ok": False, "checked": expected_seq - 1, "first_bad_seq": e["seq"],
                    "reason": "sequence gap or reorder"}
        if e["prev_hash"] != prev:
            return {"ok": False, "checked": expected_seq - 1, "first_bad_seq": e["seq"],
                    "reason": "prev_hash mismatch"}
        if entry_hash(prev, e) != e["entry_hash"]:
            return {"ok": False, "checked": expected_seq - 1, "first_bad_seq": e["seq"],
                    "reason": "entry_hash mismatch (record altered)"}
        prev = e["entry_hash"]
        expected_seq += 1
    return {"ok": True, "checked": len(entries), "head_hash": prev}
