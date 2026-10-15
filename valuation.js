// Kine Valuation Engine & Floor Rate Enforcement
function calculateKineValue(energyKwh, computeTokens, resourceWeight = 1.0) {
  const eBase = 10;       // 10 kWh baseline
  const cBase = 100000;   // 100,000 compute tokens baseline
  const mBase = 1.0;      // Standard regional unit

  const w1 = 0.5; // Energy weight
  const w2 = 0.5; // Compute weight
  const w3 = 0;   // Resource weight factor

  // Normalized weighted resource model
  const rawKines = ((energyKwh / eBase) * w1) + ((computeTokens / cBase) * w2) + ((resourceWeight / mBase) * w3);
  
  // Enforce protocol floor rate: 1 Kine >= USD $2.00 value equivalent
  const floorRateUSD = 2.00;
  const calculatedValue = Math.max(rawKines, 1.0); 

  return {
    kines: calculatedValue,
    minFloorUSD: calculatedValue * floorRateUSD
  };
}

module.exports = { calculateKineValue };