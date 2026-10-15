const express = require('express');
const cors = require('cors');
require('dotenv').config();

const { signup, login } = require('./auth');
const { registerResource, getLedgerEntries } = require('./ledger');
const { calculateKutsTicks } = require('./kutsTime');
const { validateIdentifier } = require('./identifierParser');
const { calculateKineValue } = require('./valuation');
const { attestResourceMeasurement } = require('./rveVerifier');
const { processTransactionState } = require('./stateMachine');

const app = express();
app.use(express.json());
app.use(cors());

// Auth Routes
app.post('/api/auth/signup', signup);
app.post('/api/auth/login', login);

// Ledger & Resource Routes
app.post('/api/ledger/register', registerResource);
app.get('/api/ledger/entries', getLedgerEntries);

// RVE & Valuation Endpoint
app.post('/api/rve/attest-and-value', (req, res) => {
  try {
    const { measurementId, energyKwh, computeTokens } = req.body;
    
    // Step 1: RVE Attestation
    const attestation = attestResourceMeasurement(measurementId, energyKwh, computeTokens);

    // Step 2: Kine Valuation
    const valuation = calculateKineValue(energyKwh, computeTokens);

    res.json({
      success: true,
      attestation,
      valuation
    });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Category-12 Fiscal Settlement State Machine Endpoint
app.post('/api/fiscal/settle', async (req, res) => {
  try {
    const { kineAmount } = req.body;
    const settlementResult = await processTransactionState(kineAmount);
    res.json({
      message: 'Category-12 Fiscal settlement processed successfully.',
      settlementResult
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// System Status & Time Route
app.get('/api/status', (req, res) => {
  res.json({
    status: 'Operational',
    masterNode: 'THRINC000',
    currentTicks: calculateKutsTicks(),
    timestamp: new Date().toISOString()
  });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Kinepool server running on port ${PORT}`);
});