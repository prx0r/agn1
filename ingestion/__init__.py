"""Core database layer — DuckDB for facts, events, measurements."""
from __future__ import annotations
import duckdb
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "lab.duckdb"

def get_db() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))

def init_schema(conn: duckdb.DuckDBPyConnection | None = None):
    """Create tables if they don't exist. Schema is intentionally loose."""
    close = False
    if conn is None:
        conn = get_db()
        close = True

    conn.execute("""
    -- Projects we're tracking
    CREATE TABLE IF NOT EXISTS projects (
        id VARCHAR PRIMARY KEY,
        name VARCHAR,
        ticker VARCHAR,
        category VARCHAR,           -- verifiable_execution, agent_economy, proof_generation, etc.
        thesis_tier VARCHAR,        -- tier1, tier2, tier3, candidate
        mcap DOUBLE,
        fdv DOUBLE,
        chain VARCHAR,
        website VARCHAR,
        github_org VARCHAR,
        docs_url VARCHAR,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Token/price snapshots (time series)
    CREATE TABLE IF NOT EXISTS price_snapshots (
        project_id VARCHAR,
        timestamp TIMESTAMP,
        price DOUBLE,
        mcap DOUBLE,
        fdv DOUBLE,
        volume_24h DOUBLE,
        holders INTEGER,
        PRIMARY KEY (project_id, timestamp)
    );

    -- GitHub repositories
    CREATE TABLE IF NOT EXISTS repos (
        id VARCHAR PRIMARY KEY,     -- owner/repo
        project_id VARCHAR,
        stars INTEGER,
        forks INTEGER,
        language VARCHAR,
        last_commit TIMESTAMP,
        open_issues INTEGER,
        description VARCHAR,
        created_at TIMESTAMP,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Developer activity (aggregated)
    CREATE TABLE IF NOT EXISTS dev_activity (
        repo_id VARCHAR,
        period VARCHAR,             -- 7d, 30d, 90d
        unique_authors INTEGER,
        commits INTEGER,
        prs_merged INTEGER,
        releases INTEGER,
        new_contributors INTEGER,
        bus_factor DOUBLE,
        measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (repo_id, period, measured_at)
    );

    -- Contracts deployed
    CREATE TABLE IF NOT EXISTS contracts (
        address VARCHAR,
        chain VARCHAR,
        project_id VARCHAR,
        contract_type VARCHAR,      -- attestation, registry, payment, etc.
        source_verified BOOLEAN,
        deployer VARCHAR,
        deployed_at TIMESTAMP,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (address, chain)
    );

    -- Claims made by projects
    CREATE TABLE IF NOT EXISTS claims (
        id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        claim_text VARCHAR,
        claim_category VARCHAR,     -- tee, zkp, revenue, users, etc.
        testable BOOLEAN,
        tested BOOLEAN DEFAULT FALSE,
        test_result VARCHAR,        -- pass, partial, fail, untested
        evidence TEXT,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_tested TIMESTAMP
    );

    -- Observations (raw facts from any source)
    CREATE TABLE IF NOT EXISTS observations (
        id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        source VARCHAR,             -- defillama, coingecko, github, onchain, etc.
        event_type VARCHAR,         -- price_change, new_repo, contract_deploy, etc.
        data JSON,
        confidence DOUBLE DEFAULT 1.0,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Downstream adoption
    CREATE TABLE IF NOT EXISTS adoption (
        project_id VARCHAR,
        consumer_project VARCHAR,
        artifact VARCHAR,           -- package name, SDK, etc.
        source VARCHAR,             -- deps.dev, npm, pypi
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (project_id, consumer_project, artifact)
    );

    -- Experiments we've run
    CREATE TABLE IF NOT EXISTS experiments (
        id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        probe_type VARCHAR,         -- deployment, attestation, inference, etc.
        status VARCHAR,             -- running, passed, failed
        result JSON,
        started_at TIMESTAMP,
        completed_at TIMESTAMP
    );

    -- Scoring
    CREATE TABLE IF NOT EXISTS scores (
        project_id VARCHAR,
        score_type VARCHAR,         -- dev_reality, thesis_fit, claim_reality, valuation, momentum
        score DOUBLE,
        components JSON,
        scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (project_id, score_type, scored_at)
    );

    -- Thesis vocabulary (for GH Archive search)
    CREATE TABLE IF NOT EXISTS thesis_terms (
        term VARCHAR PRIMARY KEY,
        category VARCHAR,
        weight DOUBLE DEFAULT 1.0
    );
    """)

    # Seed thesis terms
    conn.execute("""
    INSERT OR IGNORE INTO thesis_terms (term, category, weight) VALUES
    ('tee', 'execution', 1.0),
    ('tdx', 'execution', 1.0),
    ('sgx', 'execution', 0.8),
    ('sev-snp', 'execution', 1.0),
    ('attestation', 'execution', 1.0),
    ('remote attestation', 'execution', 1.0),
    ('confidential compute', 'execution', 1.0),
    ('confidential gpu', 'execution', 1.0),
    ('zkml', 'proof', 1.0),
    ('zktls', 'data', 1.0),
    ('proof of inference', 'proof', 1.0),
    ('verifiable inference', 'proof', 1.0),
    ('provenance', 'data', 0.8),
    ('receipts', 'verification', 0.8),
    ('erc-8004', 'identity', 1.0),
    ('erc-8183', 'payments', 1.0),
    ('x402', 'payments', 1.0),
    ('agent identity', 'identity', 1.0),
    ('agent payment', 'payments', 1.0),
    ('proof market', 'proof', 1.0),
    ('compute marketplace', 'compute', 1.0),
    ('depin', 'infrastructure', 0.6),
    ('spatial computing', 'physical', 1.0),
    ('robotics', 'physical', 1.0),
    ('agent wallet', 'identity', 1.0),
    ('agent delegation', 'identity', 1.0),
    ('machine payment', 'physical', 1.0)
    """).commit()

    if close:
        conn.close()

if __name__ == "__main__":
    init_schema()
    print("Schema initialized.")
