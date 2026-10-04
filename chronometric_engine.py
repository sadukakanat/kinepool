"""
Kinepool // KUTS Revision 8 Chronometric Engine
Engine A: T0 reference epoch, Session-Epoch tick mapping, and 11-field
base-100 positional encoding.

All arithmetic is EXACT (integers / Fractions). The previous version used
floating point, which cannot represent tick counts of ~1.1e18 (floats stop
being exact above 2**53 ~ 9e15) and produced wrong trailing digits.
"""

from datetime import datetime, timezone
from fractions import Fraction

MICROS_PER_DAY = 86_400 * 1_000_000
JD_OF_UNIX_EPOCH = Fraction(4_881_175, 2)  # JD 2440587.5 == 1970-01-01T00:00:00 UTC


def days_from_civil(y: int, m: int, d: int) -> int:
    """Days since 1970-01-01 in the proleptic Gregorian calendar.

    Works for any year including zero/negative (astronomical year numbering).
    Exact integer arithmetic (Howard Hinnant's algorithm).
    """
    y -= m <= 2
    era = y // 400  # floor division: correct for negative years
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146_097 + doe - 719_468


class ChronometricEngine:
    # KUTS Rev 8 constants
    SESSION_EPOCH_NS = 334          # T38 = 334.00 ns
    T0_YEAR, T0_MONTH, T0_DAY = -9999, 1, 1   # 00:00:00 UTC, astronomical year -9999
    BASE100_FIELDS = 11

    # ---- Julian Day helpers (exact) -------------------------------------
    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Naive datetime rejected: supply a timezone-aware UTC datetime.")
        return dt.astimezone(timezone.utc)

    def datetime_to_jdn(self, dt: datetime) -> Fraction:
        """Exact Julian Day Number (as a Fraction) of a datetime."""
        dt = self._to_utc(dt)
        days = days_from_civil(dt.year, dt.month, dt.day)
        tod_us = ((dt.hour * 60 + dt.minute) * 60 + dt.second) * 1_000_000 + dt.microsecond
        return JD_OF_UNIX_EPOCH + days + Fraction(tod_us, MICROS_PER_DAY)

    def get_t0_jdn(self) -> Fraction:
        return JD_OF_UNIX_EPOCH + days_from_civil(self.T0_YEAR, self.T0_MONTH, self.T0_DAY)

    # ---- Ticks ------------------------------------------------------------
    def compute_ticks(self, event_dt: datetime) -> int:
        """N = round( (event - T0) / 334 ns ), half-up, exact integer math."""
        dt = self._to_utc(event_dt)
        days = days_from_civil(dt.year, dt.month, dt.day) - days_from_civil(
            self.T0_YEAR, self.T0_MONTH, self.T0_DAY
        )
        tod_us = ((dt.hour * 60 + dt.minute) * 60 + dt.second) * 1_000_000 + dt.microsecond
        elapsed_us = days * MICROS_PER_DAY + tod_us
        if elapsed_us < 0:
            raise ValueError("Event precedes the T0 reference epoch.")
        # ticks = elapsed_us * 1000 ns / 334 ns, rounded half-up
        return (2 * elapsed_us * 1000 + self.SESSION_EPOCH_NS) // (2 * self.SESSION_EPOCH_NS)

    def now_ticks(self) -> int:
        return self.compute_ticks(datetime.now(timezone.utc))

    # ---- Base-100 encoding --------------------------------------------------
    def encode_base100_payload(self, tick_count: int) -> str:
        """11 base-100 fields (22 digits), most significant first, dot-separated."""
        if tick_count < 0:
            raise ValueError("tick_count must be non-negative.")
        if tick_count >= 100 ** self.BASE100_FIELDS:
            raise OverflowError("tick_count exceeds 11 base-100 fields.")
        fields, val = [], tick_count
        for _ in range(self.BASE100_FIELDS):
            fields.append(val % 100)
            val //= 100
        fields.reverse()
        return ".".join(f"{f:02d}" for f in fields)

    def generate_identifier(self, category_code: int, event_dt: datetime,
                            node_id: str, sub_tick: int) -> str:
        """[2-digit category]:[11 base-100 fields]-[Node ID].[sub-tick]"""
        if not 1 <= category_code <= 16:
            raise ValueError("category_code must be 1..16.")
        if not 0 <= sub_tick <= 99:
            raise ValueError("sub_tick must be 0..99.")
        return self.compose_identifier(category_code, self.compute_ticks(event_dt), node_id, sub_tick)

    def compose_identifier(self, category_code: int, ticks: int, node_id: str, sub_tick: int) -> str:
        return f"{category_code:02d}:{self.encode_base100_payload(ticks)}-{node_id}.{sub_tick:02d}"


if __name__ == "__main__":
    eng = ChronometricEngine()
    gw = datetime(2015, 9, 14, 9, 50, 45, 390000, tzinfo=timezone.utc)
    ident = eng.generate_identifier(3, gw, "THR", 1)
    expected = "03:00.01.13.51.71.67.97.76.61.67.66-THR.01"
    print("GW150914 ticks :", eng.compute_ticks(gw))
    print("Identifier     :", ident)
    print("Expected       :", expected)
    print("PASS" if ident == expected else "FAIL")