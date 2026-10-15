const crypto = require('crypto');

// Tracks consumed measurement IDs to prevent double-counting
const verifiedMeasurements = new Set();

function attestResourceMeasurement(measurementId, energyKwh, computeTokens) {
  if (verifiedMeasurements.has(measurementId)) {
    throw new Error('Double-counting prevention: Measurement ID has already been consumed.');
  }

  // Generate cryptographic attestation proof
  const timestamp = new Date().toISOString();
  const rawData = `${measurementId}:${energyKwh}:${computeTokens}:${timestamp}`;
  const signature = crypto.createHmac('sha256', process.env.JWT_SECRET || 'rve_secret')
                          .update(rawData)
                          .digest('hex');

  verifiedMeasurements.add(measurementId);

  return {
    measurementId,
    attested: true,
    signature,
    timestamp
  };
}

module.exports = { attestResourceMeasurement };