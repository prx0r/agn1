"""Scoring framework — DEV_REALITY, THESIS_FIT, CLAIM_REALITY, VALUATION."""
from __future__ import annotations
import json
from typing import Any

def score_dev_reality(conn, project_id: str) -> dict[str, Any]:
    """Score developer reality from GitHub data.

    Components:
    - 20% active real humans
    - 15% release velocity
    - 15% meaningful code velocity
    - 15% external contributor quality
    - 10% bus factor
    - 10% downstream adoption
    - 5% issue/PR responsiveness
    - 5% security engineering
    - 5% maintainer history
    """
    # Get latest dev activity
    rows = conn.execute("""
        SELECT * FROM dev_activity
        WHERE repo_id LIKE ?
        ORDER BY measured_at DESC LIMIT 10
    """, [f"%{project_id}%"]).fetchall()

    if not rows:
        return {"score": 0, "components": {}, "status": "no_data"}

    cols = [desc[0] for desc in conn.description]
    activities = [dict(zip(cols, row)) for row in rows]

    # Get observations
    obs_rows = conn.execute("""
        SELECT data FROM observations
        WHERE project_id = ? AND event_type = 'repo_analysis'
        ORDER BY observed_at DESC LIMIT 5
    """, [project_id]).fetchall()

    analyses = [json.loads(row[0]) for row in obs_rows] if obs_rows else []

    # Active humans (20%)
    total_authors = sum(a.get("unique_authors", 0) for a in activities)
    avg_authors = total_authors / max(len(activities), 1)
    active_humans_score = min(avg_authors / 10, 1.0) * 20  # 10+ authors = full score

    # Bus factor (10%)
    bus_factors = [a.get("bus_factor_top_pct", 100) for a in analyses if "bus_factor_top_pct" in a]
    avg_bus = sum(bus_factors) / max(len(bus_factors), 1) if bus_factors else 100
    bus_score = max(0, (100 - avg_bus) / 100) * 10  # Lower top% = better

    # Code velocity (15%)
    total_commits_30d = sum(a.get("commits", 0) for a in activities)
    velocity_score = min(total_commits_30d / 100, 1.0) * 15

    # Total score
    total = active_humans_score + bus_score + velocity_score
    total = min(total, 100)

    return {
        "score": round(total, 1),
        "components": {
            "active_humans": round(active_humans_score, 1),
            "bus_factor": round(bus_score, 1),
            "velocity": round(velocity_score, 1),
        },
        "status": "scored",
    }

def score_thesis_fit(conn, project_id: str) -> dict[str, Any]:
    """Score how well a project fits the verifiable autonomous infrastructure thesis."""
    from ingestion.entities import ENTITY_MAP

    entity = ENTITY_MAP.get(project_id, {})
    category = entity.get("category", "")

    # Category scores
    category_scores = {
        "verifiable_execution": 25,
        "agent_economy": 23,
        "attested_compute": 22,
        "proof_generation": 20,
        "data_proofs": 18,
        "physical_machines": 17,
        "physical_ai": 15,
        "data_provenance": 14,
        "decentralized_training": 13,
        "compute_orchestration": 12,
        "decentralized_compute": 10,
    }

    base_score = category_scores.get(category, 5)

    # Bonus for having GitHub repos (verifiable)
    repos = entity.get("repos", [])
    repo_bonus = min(len(repos) * 2, 5) if repos else 0

    # Bonus for crypto necessity (not just SaaS)
    crypto_necessity = {
        "verifiable_execution": 5,  # TEE attestation needs crypto
        "agent_economy": 5,         # Cross-owner coordination
        "physical_machines": 5,     # Machine identity/settlement
        "attested_compute": 4,
        "proof_generation": 4,
        "data_proofs": 3,
        "physical_ai": 3,
        "decentralized_training": 3,
        "data_provenance": 2,
        "compute_orchestration": 2,
        "decentralized_compute": 1,
    }

    necessity_bonus = crypto_necessity.get(category, 0)

    total = base_score + repo_bonus + necessity_bonus
    total = min(total, 25)

    return {
        "score": round(total, 1),
        "components": {
            "category_fit": base_score,
            "repo_verification": repo_bonus,
            "crypto_necessity": necessity_bonus,
        },
        "status": "scored",
    }

def score_valuation(conn, project_id: str) -> dict[str, Any]:
    """Score valuation quality (MC/FDV, unlocks, liquidity)."""
    # Get latest price snapshot
    row = conn.execute("""
        SELECT mcap, fdv, volume_24h FROM price_snapshots
        WHERE project_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, [project_id]).fetchone()

    if not row:
        return {"score": 0, "components": {}, "status": "no_data"}

    mcap, fdv, volume = row

    if not mcap or mcap == 0:
        return {"score": 0, "components": {}, "status": "no_mcap"}

    # MC/FDV ratio (lower is better — less future dilution)
    mc_fdv = mcap / fdv if fdv and fdv > 0 else 0
    mc_fdv_score = mc_fdv * 10  # 0-10

    # Volume/MC ratio (healthy trading)
    vol_mc = (volume / mcap * 100) if volume and mcap else 0
    vol_score = min(vol_mc / 10, 1.0) * 5  # 10% = full score

    # Size premium (smaller = more asymmetric, but riskier)
    if mcap < 5_000_000:
        size_score = 5  # Micro, highest asymmetric potential
    elif mcap < 20_000_000:
        size_score = 4
    elif mcap < 50_000_000:
        size_score = 3
    else:
        size_score = 2

    total = mc_fdv_score + vol_score + size_score
    total = min(total, 10)

    return {
        "score": round(total, 1),
        "components": {
            "mc_fdv_ratio": round(mc_fdv_score, 1),
            "liquidity": round(vol_score, 1),
            "size_asymmetry": size_score,
        },
        "status": "scored",
    }

def score_all(conn, project_id: str) -> dict[str, Any]:
    """Run all scoring and store results."""
    dev = score_dev_reality(conn, project_id)
    thesis = score_thesis_fit(conn, project_id)
    valuation = score_valuation(conn, project_id)

    total = dev["score"] + thesis["score"] + valuation["score"]

    result = {
        "project_id": project_id,
        "total_score": round(total, 1),
        "dev_reality": dev,
        "thesis_fit": thesis,
        "valuation": valuation,
    }

    # Store scores
    for score_type, score_data in [("dev_reality", dev), ("thesis_fit", thesis), ("valuation", valuation)]:
        conn.execute("""
            INSERT OR REPLACE INTO scores (project_id, score_type, score, components, scored_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [project_id, score_type, score_data["score"], json.dumps(score_data["components"])])

    return result

if __name__ == "__main__":
    from ingestion import get_db
    from ingestion.entities import ENTITY_MAP

    conn = get_db()
    for project_id in ENTITY_MAP:
        result = score_all(conn, project_id)
        print(f"{project_id}: {result['total_score']:.1f}")
        for k, v in result.items():
            if isinstance(v, dict) and "score" in v:
                print(f"  {k}: {v['score']}")
    conn.close()
