# Crypto Lab

Living laboratory for verifiable autonomous infrastructure thesis.

## What This Is

Not another crypto dashboard. A system that:
1. **Ingests** data from free sources (DefiLlama, GitHub, CoinGecko, on-chain)
2. **Resolves** entities (projects → repos → contracts → teams → tokens)
3. **Scores** continuously (DEV_REALITY, THESIS_FIT, CLAIM_REALITY)
4. **Discovers** new projects before CoinGecko (ERC-8004, x402, ETHGlobal, GitHub search)
5. **Tests** claims by running probes against live networks

## Architecture

```
DISCOVERY (what's out there?)
    ↓
INGESTION (pull free data)
    ↓
DUCKDB (facts, events, measurements)
    ↓
HYDRADB (relationships, graph, history)
    ↓
SCORING (rank continuously)
    ↓
AGENTS (scout + analyst + probes)
```

## Directory Structure

```
crypto-lab/
├── data/                  # DuckDB database + Parquet files
├── ingestion/             # Data collection scripts
│   ├── defillama.py       # Fees, revenue, protocols, unlocks
│   ├── coingecko.py       # Prices, mcap, categories
│   ├── github.py          # GH Archive + repo analysis
│   ├── onchain.py         # Contract deployments, Sourcify
│   └── discovery.py       # ERC-8004, x402, ETHGlobal scouting
├── graph/                 # HydraDB relationship layer
├── probes/                # Live network tests
├── agent/                 # Scout + analyst agents
└── northstar/             # Thesis docs (symlink to /root/northstar)
```

## Quick Start

```bash
pip install duckdb httpx
python -m ingestion.defillama   # Pull DefiLlama data
python -m ingestion.coingecko   # Pull CoinGecko data
python agent/scout.py           # Find new projects
python agent/analyst.py         # Score what we have
```

## Thesis

Verifiable autonomous infrastructure. The stack:
- Identity (ERC-8004)
- Execution (PHA, ACU)
- Payments (x402)
- Agent↔Agent (OLAS)
- Physical machines (PEAQ, AUKI)
- Proofs (LA, BREV)
- Data (ZKP, OPEN)
- Training (FLOCK)

## Key Rule

**Never rank by transaction count.** Rank by independently verified economic relationships.
