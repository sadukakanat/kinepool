"""
Kinepool // KUTS Revision 8 Valuation Engine (Engine D)
Kine calculation, $2.00 floor rate, and the 3.0% PFS/RSP split.

All money/Kine math uses Decimal and is stored as integer "e8" units
(1 Kine = 100_000_000 e8) so nothing is ever a float.
"""

from decimal import Decimal, localcontext, ROUND_HALF_EVEN

E8 = Decimal(10) ** 8
QUANT = Decimal("0.00000001")


def to_e8(value: Decimal) -> int:
    return int((value * E8).to_integral_value(rounding=ROUND_HALF_EVEN))


def fmt_e8(units: int) -> str:
    sign = "-" if units < 0 else ""
    units = abs(units)
    return f"{sign}{units // 10**8}.{units % 10**8:08d}"


class ValuationEngine:
    KINE_FLOOR_RATE_USD = Decimal("2.00")
    E_BASE = Decimal("10")          # kWh per 1 K-equivalent base
    C_BASE = Decimal("100000")      # compute tokens per 1 K-equivalent base
    M_BASE = Decimal("1")
    W1, W2, W3 = Decimal("0.5"), Decimal("0.5"), Decimal("0")
    PFS_RATE = Decimal("0.015")     # Protocol Fiscal Sweep
    RSP_RATE = Decimal("0.015")     # Regenerative Stewardship Pool
    TOKENS_PER_MTOK = Decimal("1000000")

    def calculate_kines(self, energy_kwh: Decimal, compute_mtok: Decimal,
                        resource_weight: Decimal = Decimal("1")) -> Decimal:
        """Total K = (E/E_base)*w1 + (C/C_base)*w2 + (M/M_base)*w3"""
        with localcontext() as ctx:
            ctx.prec = 60
            tokens = compute_mtok * self.TOKENS_PER_MTOK
            total = ((energy_kwh / self.E_BASE) * self.W1
                     + (tokens / self.C_BASE) * self.W2
                     + (resource_weight / self.M_BASE) * self.W3)
            return max(Decimal(0), total).quantize(QUANT, rounding=ROUND_HALF_EVEN)

    def settle(self, energy_kwh: Decimal, compute_mtok: Decimal) -> dict:
        """Returns integer e8 amounts. Invariant: pfs + rsp + net == raw."""
        with localcontext() as ctx:
            ctx.prec = 60
            raw = self.calculate_kines(energy_kwh, compute_mtok)
            if raw <= 0:
                raise ValueError("Resource inputs produce zero Kines; enter energy and/or compute.")
            usd = (raw * self.KINE_FLOOR_RATE_USD).quantize(QUANT, rounding=ROUND_HALF_EVEN)
            pfs = (raw * self.PFS_RATE).quantize(QUANT, rounding=ROUND_HALF_EVEN)
            rsp = (raw * self.RSP_RATE).quantize(QUANT, rounding=ROUND_HALF_EVEN)
            net = raw - pfs - rsp
            flux = raw * 100            # 1 K = 100 Flux
            dyne = raw / 100            # 1 Dyne = 100 K
        return {
            "raw_kines_e8": to_e8(raw),
            "valuation_usd_e8": to_e8(usd),
            "pfs_e8": to_e8(pfs),
            "rsp_e8": to_e8(rsp),
            "net_e8": to_e8(net),
            "flux_units": str(flux.quantize(Decimal("0.01"))),
            "dyne_units": str(dyne.quantize(Decimal("0.000001"))),
            "floor_rate_usd": str(self.KINE_FLOOR_RATE_USD),
        }


if __name__ == "__main__":
    s = ValuationEngine().settle(Decimal("50"), Decimal("5"))
    print({k: (fmt_e8(v) if k.endswith("_e8") else v) for k, v in s.items()})
