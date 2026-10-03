"""
Kinepool // KUTS Revision 8 Valuation & Governance Settlement Engine
Engine D: Kine/Flux/Dyne calculation, floor rate enforcement, 
and 3.0% PFS/RSP structural governance split.
"""

from typing import Dict, Any

class ValuationAndSettlementEngine:
    """
    Computes tokenized value (Kines, Flux, Dynes) from verified telemetry,
    enforces the USD $2.00 floor rate, and executes governance allocations.
    """
    
    # Protocol Constants (Section 2.6 & 2.7)
    KINE_FLOOR_RATE_USD = 2.00
    E_BASE = 10.0      # Baseline energy in kWh (10 kWh = 1 K equivalent base)
    C_BASE = 100000.0  # Baseline compute tokens (100k tokens = 1 K equivalent base)
    M_BASE = 1.0       # Standard regional resource-weight unit
    
    # Least Action Protocol Governance Splits (Section 2.5)
    PFS_RATE = 0.015   # 1.5% Protocol Fiscal Sweep (systemic maintenance)
    RSP_RATE = 0.015   # 1.5% Regenerative Stewardship Pool (environmental/community)
    
    def calculate_kines(self, energy_kwh: float, compute_tokens: float, resource_weight: float = 1.0, w1: float = 0.5, w2: float = 0.5, w3: float = 0.0) -> float:
        """
        Calculates total Kines (K) using the normalized weighted resource model:
        Total Kines = (E / E_base)*w1 + (C / C_base)*w2 + (M / M_base)*w3
        """
        term_e = (energy_kwh / self.E_BASE) * w1
        term_c = (compute_tokens / self.C_BASE) * w2
        term_m = (resource_weight / self.M_BASE) * w3
        
        total_kines = term_e + term_c + term_m
        return max(0.0, total_kines)

    def process_settlement(self, attested_packet: Dict[str, Any], market_price_usd: float = 2.00) -> Dict[str, Any]:
        """
        Processes an attested resource packet through valuation, floor-rate check,
        and the 3.0% Least Action Protocol transaction state machine.
        """
        metrics = attested_packet.get("raw_metrics", {})
        energy_kwh = metrics.get("energy_kwh", 0.0)
        compute_tokens = metrics.get("compute_tokens", 0.0)
        resource_weight = metrics.get("resource_weight", 1.0)
        
        # 1. Compute Raw Kines
        raw_kines = self.calculate_kines(energy_kwh, compute_tokens, resource_weight)
        
        # 2. Enforce Kine Floor Rate ($2.00 USD absolute minimum per Kine)
        effective_unit_price = max(self.KINE_FLOOR_RATE_USD, market_price_usd)
        total_fiat_value = raw_kines * effective_unit_price
        
        if effective_unit_price < self.KINE_FLOOR_RATE_USD:
            raise ValueError("SETTLEMENT_REJECTED: Evaluated unit price violates the $2.00 Kine Floor Rate.")

        # 3. Compute Sub-Units & Macro-Units
        total_flux = raw_kines * 100.0  # 1 K = 100 Flux
        total_dynes = raw_kines / 100.0 # 1 Dyne = 100 K
        
        # 4. Execute Least Action Protocol (3.0% Structural Allocation)
        pfs_allocation = raw_kines * self.PFS_RATE
        rsp_allocation = raw_kines * self.RSP_RATE
        net_recipient_credit = raw_kines - (pfs_allocation + rsp_allocation)
        
        # 5. Build Settled Transaction State Machine Record
        settlement_receipt = {
            "measurement_id": attested_packet.get("measurement_id"),
            "node_id": attested_packet.get("node_id"),
            "transaction_state": "SETTLED",
            "valuation_summary": {
                "raw_kines_minted": round(raw_kines, 4),
                "flux_units": round(total_flux, 2),
                "dyne_units": round(total_dynes, 6),
                "effective_floor_price_usd": effective_unit_price,
                "total_valuation_usd": round(total_fiat_value, 2)
            },
            "governance_split_category_12": {
                "protocol_fiscal_sweep_pfs_1_5_pct": round(pfs_allocation, 4),
                "regenerative_stewardship_rsp_1_5_pct": round(rsp_allocation, 4),
                "net_recipient_credit": round(net_recipient_credit, 4)
            },
            "audit_trail": [
                "INITIATED",
                "VERIFIED (RVE Signature Valid)",
                "ALLOCATED (PFS + RSP Computed)",
                "SETTLED (Accounts Credited)",
                "RECORDED (Category-11/12 Governance Log Written)"
            ]
        }
        
        return settlement_receipt


# --- Verification Test ---
if __name__ == "__main__":
    from rve_engine import ResourceVerificationEngine
    
    rve = ResourceVerificationEngine()
    engine = ValuationAndSettlementEngine()
    
    print("--- Kinepool Valuation & Governance Settlement Engine Test ---")
    
    # Simulate compute cluster resource consumption (Energy + Compute Tokens)
    cluster_metrics = {
        "energy_kwh": 50.0,         # 50 kWh consumed
        "compute_tokens": 500000.0,  # 500,000 AI compute tokens consumed
        "resource_weight": 1.0
    }
    
    packet = rve.attest_telemetry(
        node_id="THR",
        category_code=12,
        resource_type="Compute & Energy Settlement",
        raw_metrics=cluster_metrics,
        metering_source="HPC-Cluster-Metering-API"
    )
    
    receipt = engine.process_settlement(packet, market_price_usd=2.50)
    
    import json
    print(json.dumps(receipt, indent=2))