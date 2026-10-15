const pool = require('./database');
const { validateIdentifier } = require('./identifierParser');

// Create ledger table if not exists
pool.query(`
  CREATE TABLE IF NOT EXISTS ledger_entries (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(128) UNIQUE NOT NULL,
    category_code VARCHAR(2) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    kine_value NUMERIC(18, 4) NOT NULL,
    status VARCHAR(32) DEFAULT 'VERIFIED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
`).catch(err => console.error("Ledger table creation error:", err));

async function registerResource(req, res) {
  try {
    const { identifier, categoryCode, userId, resourceName, kineValue } = req.body;

    if (!validateIdentifier(identifier)) {
      return res.status(400).json({ error: 'Invalid KUTS composite identifier grammar.' });
    }

    const query = `
      INSERT INTO ledger_entries (identifier, category_code, user_id, resource_name, kine_value)
      VALUES ($1, $2, $3, $4, $5) RETURNING *;
    `;
    const values = [identifier, categoryCode, userId, resourceName, kineValue];
    const result = await pool.query(query, values);

    res.status(201).json({
      message: 'Resource registered successfully on Kinepool ledger.',
      entry: result.rows[0]
    });
  } catch (err) {
    console.error('Ledger registration error:', err);
    res.status(500).json({ error: 'Internal server error during registration.' });
  }
}

async function getLedgerEntries(req, res) {
  try {
    const result = await pool.query('SELECT * FROM ledger_entries ORDER BY created_at DESC LIMIT 50');
    res.json(result.rows);
  } catch (err) {
    console.error('Fetch ledger error:', err);
    res.status(500).json({ error: 'Failed to fetch ledger entries.' });
  }
}

module.exports = { registerResource, getLedgerEntries };