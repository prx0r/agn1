"""Scout agent — discovers new projects from multiple sources."""
from __future__ import annotations
import json
import asyncio
from typing import Any

async def scout_cycle(conn) -> dict[str, Any]:
    """Run one full scout cycle: discovery + ingestion + entity resolution."""
    from ingestion.defillama import run_defillama_ingestion
    from ingestion.coingecko import run_coingecko_ingestion
    from ingestion.discovery import run_discovery
    from ingestion.entities import ENTITY_MAP

    results = {}

    # 1. Ingest from free sources
    print("[scout] Running DefiLlama ingestion...")
    results["defillama"] = await run_defillama_ingestion(conn)

    print("[scout] Running CoinGecko ingestion...")
    targets = list(ENTITY_MAP.keys())
    results["coingecko"] = await run_coingecko_ingestion(conn, targets)

    # 2. Discovery (GitHub + ETHGlobal)
    print("[scout] Running discovery pipeline...")
    results["discovery"] = await run_discovery(conn)

    # 3. Store all discovered projects as candidates
    obs_rows = conn.execute("""
        SELECT DISTINCT project_id, data FROM observations
        WHERE source = 'discovery'
        ORDER BY observed_at DESC LIMIT 100
    """).fetchall()

    for row in obs_rows:
        project_id = row[0]
        data = json.loads(row[1]) if row[1] else {}

        # Check if already tracked
        existing = conn.execute(
            "SELECT id FROM projects WHERE id = ?", [project_id]
        ).fetchone()

        if not existing:
            conn.execute("""
                INSERT OR REPLACE INTO projects (id, name, category, thesis_tier, last_updated)
                VALUES (?, ?, ?, 'candidate', CURRENT_TIMESTAMP)
            """, [
                project_id,
                data.get("name", project_id),
                data.get("category", "unknown"),
            ])

    return results

async def monitor_cycle(conn) -> dict[str, Any]:
    """Quick monitoring cycle — check for changes in tracked projects."""
    from ingestion.coingecko import fetch_coin_detail, store_coin_detail

    # Get all tracked projects
    rows = conn.execute("SELECT id FROM projects WHERE thesis_tier != 'candidate'").fetchall()
    project_ids = [row[0] for row in rows]

    changes = []
    for pid in project_ids:
        detail = await fetch_coin_detail(pid)
        if detail:
            store_coin_detail(conn, pid, detail)
            changes.append(pid)

    return {"monitored": len(project_ids), "updated": len(changes)}

if __name__ == "__main__":
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)

    result = asyncio.run(scout_cycle(conn))
    print(f"[scout] Cycle complete: {result}")
    conn.close()
