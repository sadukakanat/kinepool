"""
KUTS Valuation Engine (Revision 8)
Calculates tokenized Kine (Ꝃ) yields based on energy ($E$) and compute ($C$) components,
enforces the $2.00 USD floor rate, and computes the 3.0% Least Action Protocol split (PFS/RSP).
"""

class ValuationEngine:
    FLOOR_RATE_USD = 2.00
    LAP_SPLIT_RATE = 0.03  # 3.0% Total Least Action Protocol split
    PFS_RATIO = 0.5        # 1.5% allocation
    RSP_RATIO = 0.5        # 1.5% allocation

    @staticmethod
    def calculate_kines(kwh: float, compute_tokens: float) -> dict:
        """
        Calculates minted Kines and economic valuation based on resource metrics:
        - Energy Component (E): (kWh / 10.0) * 0.5
        - Compute Component (C): (Compute / 0.1) * 0.5
        """
        energy_component = (max(0.0, kwh) / 10.0) * 0.5
        compute_component = (max(0.0, compute_tokens) / 0.1) * 0.5
        
        total_kines = max(0.0, energy_component + compute_component)
        
        # Enforce $2.00 floor rate per Kine
        floor_usd_value = total_kines * ValuationEngine.FLOOR_RATE_USD

        # Least Action Protocol 3.0% Split (1.5% PFS, 1.5% RSP)
        pfs_kines = total_kines * (ValuationEngine.LAP_SPLIT_RATE * ValuationEngine.PFS_RATIO)
        rsp_kines = total_kines * (ValuationEngine.LAP_SPLIT_RATE * ValuationEngine.RSP_RATIO)

        return {
            "total_kines": round(total_kines, 4),
            "floor_usd_value": round(floor_usd_value, 2),
            "pfs_split_kines": round(pfs_kines, 4),
            "rsp_split_kines": round(rsp_kines, 4),
            "floor_rate_enforced": ValuationEngine.FLOOR_RATE_USD
        }

if __name__ == "__main__":
    engine = ValuationEngine()
    print("Testing Valuation Engine...")
    test_result = engine.calculate_kines(kwh=100.0, compute_tokens=1.0)
    print("Valuation Output:", test_result)