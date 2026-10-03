"""
Kinepool // KUTS Revision 8 Chronometric Engine
Engine A: Handles T0 reference epoch, JDN conversion, Session-Epoch mapping, 
and 11-field base-100 positional encoding.
"""

from datetime import datetime, timezone
import math

class ChronometricEngine:
    # Authoritative Constants per KUTS Revision 8 Specification
    SESSION_EPOCH_DURATION = 3.340e-7  # T38 in seconds (334.00 ns)
    
    def __init__(self):
        # T0 reference epoch: 00:00:00 UTC on proleptic Gregorian year -9999
        # In astronomical year numbering, year -9999 corresponds to proleptic year -9999.
        # We handle this via standard Julian Day Number (JDN) calculations.
        pass

    @staticmethod
    def datetime_to_jdn(dt: datetime) -> float:
        """
        Converts a datetime object to a Julian Day Number (JDN) on the 
        proleptic Gregorian calendar with astronomical year numbering.
        """
        year = dt.year
        month = dt.month
        day = dt.day
        
        # Astronomical year adjustment for proleptic Gregorian
        if month <= 2:
            year -= 1
            month += 12
            
        A = math.floor(year / 100)
        B = 2 - A + math.floor(A / 4)
        
        # JDN integer core for the date
        jdn_date = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5
        
        # Add fraction of day from hours, minutes, seconds, microseconds
        day_fraction = (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6) / 86400.0
        
        return jdn_date + day_fraction

    def get_to_jdn(self) -> float:
        """
        Calculates JDN for T0 (00:00:00 on proleptic Gregorian astronomical year -9999).
        Astronomical year -9999 translates in standard chronological math to year -9999.
        """
        # Using a reference constructor for astronomical year -9999, Jan 1st
        # Python datetime doesn't support negative years directly below year 1 natively in standard library without shift,
        # so we compute JDN directly using algorithm mapping for year -9999.
        target_year = -9999
        # Proleptic Gregorian formula mapping for -9999-01-01 00:00:00 UTC
        # Base JDN for year -9999 computed via standard astronomical formula:
        # JDN = 365.25*(Y+4716) ... 
        month = 1
        day = 1
        year = target_year
        if month <= 2:
            year -= 1
            month += 12
        A = math.floor(year / 100)
        B = 2 - A + math.floor(A / 4)
        jdn_t0 = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5
        return jdn_t0

    def compute_ticks(self, event_dt: datetime) -> int:
        """
        Computes elapsed Session-Epoch ticks (N) from T0 to event instant.
        N = round( [ (JDN(E) - JDN(T0)) * 86400 ] / 3.340e-7 )
        """
        jdn_event = self.datetime_to_jdn(event_dt)
        jdn_t0 = self.get_to_jdn()
        
        elapsed_days = jdn_event - jdn_t0
        elapsed_seconds = elapsed_days * 86400.0
        
        # Division by Session-Epoch duration with nearest-integer rounding
        tick_count_float = elapsed_seconds / self.SESSION_EPOCH_DURATION
        return round(tick_count_float)

    def encode_base100_payload(self, tick_count: int) -> str:
        """
        Encodes an integer tick count into an 11-field base-100 positional payload string 
        (22 decimal digits, zero-padded, dot-separated).
        Each field represents values 00 to 99. Base-100 means shifting by powers of 100.
        """
        fields = []
        val = tick_count
        
        # Extract 11 base-100 fields from least significant to most significant, then reverse
        for _ in range(11):
            fields.append(val % 100)
            val //= 100
            
        fields.reverse()
        
        # Format each field as a 2-digit zero-padded string
        return ".".join(f"{f:02d}" for f in fields)

    def generate_identifier(self, category_code: int, event_dt: datetime, node_id: str, sub_tick: int) -> str:
        """
        Assembles the complete KUTS composite identifier:
        [2-Digit Category]:[11 Base-100 Fields]-[Anchor Node ID].[Sub-Tick Counter]
        """
        ticks = self.compute_ticks(event_dt)
        payload = self.encode_base100_payload(ticks)
        
        cat_str = f"{category_code:02d}"
        sub_tick_str = f"{sub_tick:02d}"
        
        return f"{cat_str}:{payload}-{node_id}.{sub_tick_str}"


# --- Verification Test: GW150914 Test Case (Section 9.2) ---
if __name__ == "__main__":
    engine = ChronometricEngine()
    
    # GW150914 Event Timestamp: 14 September 2015, 09:50:45.39 UTC
    gw_time = datetime(2015, 9, 14, 9, 50, 45, 390000, tzinfo=timezone.utc)
    
    ticks = engine.compute_ticks(gw_time)
    payload = engine.encode_base100_payload(ticks)
    full_id = engine.generate_identifier(category_code=3, event_dt=gw_time, node_id="THR", sub_tick=1)
    
    print("--- Kinepool Chronometric Engine Test ---")
    print(f"Calculated Ticks (N): {ticks}")
    print(f"Base-100 Payload:     {payload}")
    print(f"Composite Identifier: {full_id}")
    print(f"Expected Identifier:  03:00.01.13.51.71.67.97.76.61.67.66-THR.01")