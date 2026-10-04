"""
Kinepool // KUTS Revision 8 Uniqueness & NodeID Engine (Engine B).

Pure validation helpers. Sub-tick allocation is DATABASE-backed (see
ledger_service.allocate_sub_tick) so it survives restarts and is atomic.

ASSUMPTION TO VERIFY AGAINST SECTION 4.2 OF THE MASTER TEMPLATE:
callsign = 3 uppercase letters + 0-6 digits (as before); full registry ID is
the callsign letters followed by up to 12 more uppercase letters/digits
(e.g. THRINC000). The old code could not accept THRINC000 under its own regex.
"""

import re

CALLSIGN_PATTERN = re.compile(r"^[A-Z]{3}[0-9]{0,6}$")
FULL_ID_PATTERN = re.compile(r"^[A-Z]{3}[A-Z0-9]{0,12}$")
SUB_TICK_MAX = 99


class NodeIDRegistry:
    @staticmethod
    def valid_callsign(value: str) -> bool:
        return bool(CALLSIGN_PATTERN.match(value or ""))

    @staticmethod
    def valid_full_id(value: str) -> bool:
        return bool(FULL_ID_PATTERN.match(value or ""))

    @staticmethod
    def consistent(callsign: str, full_id: str) -> bool:
        """Full ID must begin with its callsign's letters."""
        return (NodeIDRegistry.valid_callsign(callsign) and NodeIDRegistry.valid_full_id(full_id)
                and full_id.startswith(callsign[:3]))