# AGN1 — Frontier Autonomous-Agent Lab

*Spec v1 — 2026-08-20*

## What This Is

A living laboratory for the autonomous machine economy. One system, five outputs:

```
DISCOVER → TEST → TRACK → EVIDENCE GRAPH → API/BLOG/REPORTS
```

Not five separate systems. Not a dashboard. Not "crypto intelligence."

> What is actually being built at the frontier of autonomous agents, and what survives independent testing?

## Reference Files

| File | Role |
|---|---|
| `northstar/thesis1-proof-carrying-machine-economy.md` | Core thesis |
| `northstar/thesis2-verifiable-autonomous-infrastructure.md` | Research map, project tiers |
| `northstar/alpha1-zero-cost-intelligence-stack.md` | Data sources, scoring model, architecture |
| `northstar/alpha2-crypto-lab-living-laboratory.md` | Probe concept, claim testing, recursive architecture |
| `northstar/alpha3-revised-watchlist-discovery-pipeline.md` | Watchlist tiers, discovery sources, fundamental rule |
| `northstar/alpha4-decentralized-ai-compute-relative-value-deep-dive.md` | Analytical output we want to automate |
| `northstar/alpha5-frontier-lab-strategic-blueprint.md` | Product architecture, business model, V0 structure |

## Principles

1. **Evidence over opinion.** Every claim gets tested or flagged untested.
2. **Transformation over state.** The graph records how things changed, not just what is.
3. **Independence over volume.** 12 independent actors > 1M transactions.
4. **Modular over monolithic.** Every module works independently, composes cleanly.
5. **Earned complexity.** Don't build what we don't need yet. HydraDB when agent memory needs it. Site when we have something to show.

---

## Directory Structure

```
crypto-lab/                          # or rename to frontier-lab/
│
├── AGENTS.md                        # operating rules
├── SPEC.md                          # this file
├── pyproject.toml
│
├── data/
│   ├── lab.duckdb                   # canonical facts/events/measurements
│   └── reports/                     # generated reports
│
├── ingestion/                       # data collection modules
│   ├── __init__.py                  # DuckDB connection + schema
│   ├── defillama.py                 # TVL, fees, revenue, raises
│   ├── coingecko.py                 # prices, mcap, FDV
│   ├── github.py                    # repo analysis via GH Archive / API
│   ├── bittensor.py                 # subnet chain data
│   ├── openrouter.py                # provider traffic stats
│   ├── discovery.py                 # ERC-8004, x402, ETHGlobal scouting
│   └── entities.py                  # entity resolution + ENTITY_MAP
│
├── scout/                           # discovery + monitoring
│   ├── __init__.py
│   ├── scout.py                     # find new projects/repos/people
│   ├── monitor.py                   # track changes in known projects
│   └── papers.py                    # arXiv + OpenAlex research feed
│
├── lab/                             # experimental infrastructure
│   ├── __init__.py
│   ├── runner.py                    # execute experiments
│   ├── probes/                      # per-project test suites
│   │   ├── phala/
│   │   ├── acurast/
│   │   ├── chutes/
│   │   └── _template/
│   └── results/                     # experiment output bundles
│
├── agent/                           # analysis + scoring
│   ├── __init__.py
│   ├── scoring.py                   # DEV_REALITY, THESIS_FIT, CLAIM_REALITY, VALUATION
│   ├── analyst.py                   # report generation
│   ├── claims.py                    # claim extraction + falsification
│   └── decisions.py                 # Research Decision Records
│
├── graph/                           # HydraDB layer
│   ├── __init__.py
│   ├── hydra_sync.py                # DuckDB → HydraDB sync
│   ├── queries.py                   # graph traversal queries
│   └── timeline.py                  # temporal transformation queries
│
├── people/                          # GitGoblin — people intelligence
│   ├── __init__.py
│   ├── provenance.py                # developer trajectory tracking
│   └── contributors.py              # cross-project contributor mapping
│
├── web/                             # public surface (V1)
│   ├── api.py                       # FastAPI endpoints
│   └── templates/                   # project pages
│
├── bittensor/                       # Bittensor-specific modules
│   ├── __init__.py
│   ├── subnets.py                   # subnet registry + data
│   ├── emissions.py                 # emission tracking + analysis
│   ├── radar.py                     # BITTENSOR RADAR output
│   └── autopsies.py                 # incentive mechanism autopsies
│
├── run.py                           # pipeline orchestrator
└── tests/                           # test suite
```

---

## Module Specs

### 1. Ingestion (`ingestion/`)

**Purpose:** Pull deterministic data into DuckDB. No LLM in the ingestion path.

**Current state:** defillama.py, coingecko.py, discovery.py, entities.py exist and partially work.

**Additions needed:**

| Module | Source | Data | Free? |
|---|---|---|---|
| `bittensor.py` | bittensor.ai API | subnet data, emissions, miners, validators | Yes |
| `openrouter.py` | openrouter.ai/providers | provider traffic, tokens/day, retention | Yes |
| `github.py` | GH Archive + GitHub API | commits, PRs, contributors, releases | Yes |

**Schema原则:** Keep the existing DuckDB schema. Add tables only when a new data type doesn't fit existing ones. Don't create 85 edge types upfront.

### 2. Scout (`scout/`)

**Purpose:** Find interesting things before they're obvious.

**Inputs:** GitHub combinations, ERC-8004 registry, x402 ecosystem, ETHGlobal showcase, arXiv, DefiLlama adapter PRs, standards diffs.

**Key queries from alpha3:**
```
"ERC-8004" + "TEE"
"x402" + "MCP"
"agent" + "remote attestation"
"agent" + "TDX"
...
```

**Output:** Observations in DuckDB. New projects → `projects` table as `thesis_tier: candidate`.

### 3. Lab (`lab/`)

**Purpose:** Run reproducible experiments against live networks.

**Architecture:**
```
lab/
  probes/
    _template/
      spec.json          # what to test, expected results
      run.py             # execution script
      verify.py          # verification script
      RESULTS.md         # human-readable output
    phala/
      attestation/
      deployment/
      ...
    acurast/
      job-execution/
      ...
```

**Runner:** `lab/runner.py` takes a probe spec, executes it, stores results in DuckDB `experiments` table.

**Output bundles:** Every experiment produces a reproducible bundle:
```
lab/results/
  exp-0042-phala-attestation/
    spec.json
    output.json
    evidence.json
    hash: sha256(gold ‖ code ‖ config) → out_hash
```

### 4. Agent (`agent/`)

**Purpose:** Score, analyze, extract claims, maintain Research Decision Records.

**Scoring (from alpha1):**
```
THESIS_FIT        0–25   category + crypto necessity + repos
DEV_REALITY       0–20   active humans, velocity, bus factor, adoption
CLAIM_REALITY     0–25   tested claims vs untested (NEW — not implemented)
VALUATION         0–10   MC/FDV, liquidity, size
MOMENTUM          0–20   change in above scores over time (NEW)
```

**Claims:** Extract falsifiable claims from project docs/GitHub. Mark testable. Assign to probes. Track test results.

**Research Decision Records:** Store structured reasoning (see alpha5 for format). Hash artifacts for traceability. Enable epistemic history.

### 5. Graph (`graph/`)

**Purpose:** HydraDB layer for temporal transformation queries.

**When:** After we have enough data that graph queries become useful. Not day one.

**Design (from alpha5):** Record how things changed:
```
PHA
 ├─ 2021 → confidential smart contracts
 ├─ 2024 → dstack
 ├─ 2026 → agent CVMs
 ├─ IMPLEMENTS → TDX
 └─ TESTED_BY → experiment #421
```

**Sync:** DuckDB remains canonical. HydraDB gets fed important observations for agent memory + relationship queries.

### 6. People (`people/`)

**Purpose:** GitGoblin — follow builders, not tickers.

**Tracks:** developer → repos, papers, companies, standards, collaborations. Temporal trajectory.

**Input:** GitHub contributor data, paper authorship, ETHGlobal participation, company affiliations.

### 7. Bittensor (`bittensor/`)

**Purpose:** Treat every subnet as an experiment in incentive-designed machine intelligence.

**Modules:**
- `subnets.py` — registry of all subnets, what they incentivize
- `emissions.py` — emission concentration, subsidy intensity
- `radar.py` — BITTENSOR RADAR output (from alpha5)
- `autopsies.py` — incentive mechanism deep dives

**Key metric:** external revenue / token emissions ratio.

### 8. Web (`web/`)

**Purpose:** Free public surface. Marketing for deeper intelligence.

**When:** After we have 20 scored projects + 3 experiments + 1 report.

**Endpoints (from alpha5):**
```
GET /api/v1/search
GET /api/v1/projects
GET /api/v1/projects/{id}
GET /api/v1/people
GET /api/v1/timeline/{id}
GET /api/v1/claims/{id}
GET /api/v1/experiments
GET /api/v1/subnets
GET /api/v1/health
```

---

## The Fundamental Rule

From alpha3, encoded everywhere:

> **Never rank by transaction count.**

```yaml
WEAK: 1,000,000 transactions between wallets controlled by same entity
STRONG: 12 independent developers running 9 unrelated agents buying
        services from 7 independent operators for actual money over 6 months
```

Fundamental unit: **independently verified economic relationship**.

---

## V0 Milestone

Brutally simple. From alpha5:

- [ ] 20 projects scored
- [ ] 5 Bittensor subnets analyzed
- [ ] 3 reproducible experiments
- [ ] 1 useful public report
- [ ] 1 `/search` API

Only after that does Otto get a Twitter account.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Facts/events | DuckDB | Already installed, fast, local, SQL |
| Graph/memory | HydraDB | Temporal, versioned, Python SDK, MCP server |
| Ingestion | httpx | Already installed, async |
| API | FastAPI + uvicorn | Already installed |
| Experiments | Python scripts + JSON bundles | Simple, reproducible, hashable |
| Reports | Markdown | Machine + human readable |
| MCP | HydraDB MCP server | Expose our data to agents |

No Kafka. No microservices. No custom blockchain. No giant ontology. No vector database + Postgres + ClickHouse.
