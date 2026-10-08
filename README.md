# Kinepool: Decentralized Resource Ledger & Chronometric Platform
## Specification: KUTS Revision 8
### Master Origin Node: THRINC000 (Thrissur, Kerala, India)

Kinepool is an advanced, decentralized resource-ledger and chronometric synchronization ecosystem built on the **Kinetic Unified Temporal Synchronization (KUTS Revision 8)** framework. It governs asset minting, tamper-evident audit logging, Least Action Protocol (LAP) splits, and spatial-temporal anchoring across a global node network.

---

## Architecture & Tech Stack
* **Backend:** FastAPI, SQLite, Pydantic, Uvicorn (`main.py`)
* **Engines:** Chronometric Engine, Resource-Verification Engine (RVE), Valuation Engine, Integrity Engine, Uniqueness Engine.
* **Frontend Portal Suite:** Modernized dark-mode HTML/Tailwind CSS interfaces (`dashboard.html`, `genesis-gateway.html`, `temporal-converter.html`, `b2b-escrow.html`, `freight-router.html`, `my-task.html`, `star-hunter.html`, `wallet-ledger.html`).
* **Deployment Target:** Render (`https://kinepool.onrender.com`)

---

## Core Protocol Parameters
* **Floor Valuation:** \$2.00 / Ꝃ
* **LAP Split:** 3.0% total (1.5% Protocol Fee Sweep / 1.5% Regenerative Stewardship Pool)
* **Chronometric Precision Bound:** $\le 334.00\text{ ns}$ uncertainty limit.

---

## Local Development & Startup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt