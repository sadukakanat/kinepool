const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const pool = require('./database');

async function signup(req, res) {
  try {
    const { email, password, assignedNode = 'THR' } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required.' });
    }

    const userCheck = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
    if (userCheck.rows.length > 0) {
      return res.status(400).json({ error: 'Email is already registered.' });
    }

    const userId = `KINE-${uuidv4().substring(0, 8).toUpperCase()}`;
    const rawKey = `KP-KEY-${uuidv4()}`;

    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);
    const keyHash = await bcrypt.hash(rawKey, salt);

    await pool.query(
      `INSERT INTO users (user_id, email, password_hash, kinepool_key_hash, assigned_node) VALUES ($1, $2, $3, $4, $5)`,
      [userId, email, passwordHash, keyHash, assignedNode]
    );

    // Return rawKey ONLY ONCE upon creation
    res.status(201).json({
      message: 'Account initialized successfully.',
      userId,
      kinepoolKey: rawKey,
      assignedNode
    });
  } catch (err) {
    console.error('Signup error:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
}

async function login(req, res) {
  try {
    const { email, password } = req.body;
    const result = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }

    const user = result.rows[0];
    const isMatch = await bcrypt.compare(password, user.password_hash);

    if (!isMatch) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }

    const token = jwt.sign(
      { userId: user.user_id, email: user.email, node: user.assigned_node },
      process.env.JWT_SECRET || 'fallback_secret',
      { expiresIn: '24h' }
    );

    res.json({
      message: 'Login successful.',
      token,
      userId: user.user_id,
      assignedNode: user.assigned_node
    });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
}

module.exports = { signup, login };