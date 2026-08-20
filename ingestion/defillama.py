"""DefiLlama data ingestion — free, no API key, CSV downloads + API."""
from __future__ import annotations
import httpx
import json
import time
from datetime import datetime
from typing import Any
from pathlib import Path

TIMEOUT = httpx.Timeout(30.0)
BASE = "https://api.llama.fi"
COINS = "https://coins.llama.fi"

async def fetch_protocols() -> list[dict[str, Any]]:
    """All protocols with TVL."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/protocols")
        r.raise_for_status()
        return r.json()

async def fetch_fees_overview() -> dict[str, Any]:
    """Fee/revenue overview for all protocols."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
        r.raise_for_status()
        return r.json()

async def fetch_fees_summary(protocol: str) -> dict[str, Any]:
    """Fee/revenue summary for one protocol."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/summary/fees/{protocol}?dataType=dailyFees")
        r.raise_for_status()
        return r.json()

async def fetch_revenue_summary(protocol: str) -> dict[str, Any]:
    """Revenue summary for one protocol."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/summary/fees/{protocol}?dataType=dailyRevenue")
        r.raise_for_status()
        return r.json()

async def fetch_tvl_history(protocol: str) -> list[dict]:
    """Historical TVL for a protocol."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/protocol/{protocol}")
        r.raise_for_status()
        data = r.json()
        return data.get("tvl", [])

async def fetch_yields(pools: int = 200) -> list[dict]:
    """Top yield pools."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"https://yields.llama.fi/pools")
        r.raise_for_status()
        pools_data = r.json().get("data", [])
        # Sort by TVL descending
        pools_data.sort(key=lambda x: x.get("tvlUsd", 0), reverse=True)
        return pools_data[:pools]

async def fetch_unlocks() -> list[dict]:
    """Token unlocks/emissions data."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/emissions")
        if r.status_code == 200:
            return r.json()
        return []

async def fetch_raises() -> list[dict]:
    """Fundraising data."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/raises")
        if r.status_code == 200:
            return r.json()
        return []

async def fetch_treasuries() -> list[dict]:
    """Protocol treasuries."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/treasuries")
        if r.status_code == 200:
            return r.json()
        return []

async def fetch_stablecoins() -> list[dict]:
    """Stablecoin data."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/stablecoins")
        if r.status_code == 200:
            return r.json().get("peggedAssets", [])
        return []

def store_protocols(conn, protocols: list[dict]):
    """Store protocol data into DuckDB."""
    for p in protocols:
        name = p.get("name", "")
        slug = p.get("slug", p.get("name", "")).lower().replace(" ", "-")
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'defillama', 'protocol_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"defillama-protocol-{slug}",
            slug,
            json.dumps({
                "name": name,
                "tvl": p.get("tvl"),
                "chain": p.get("chain"),
                "category": p.get("category"),
                "chains": p.get("chains", []),
                "change_1h": p.get("change_1h"),
                "change_1d": p.get("change_1d"),
                "change_7d": p.get("change_7d"),
                "mcap": p.get("mcap"),
            })
        ])

def store_fees(conn, fees_data: dict):
    """Store fee overview data."""
    protocols = fees_data.get("protocols", [])
    for p in protocols:
        name = p.get("name", p.get("defillamaId", "unknown"))
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'defillama', 'fees_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"defillama-fees-{name}",
            name.lower().replace(" ", "-"),
            json.dumps({
                "total24h": p.get("total24h"),
                "total7d": p.get("total7d"),
                "total30d": p.get("total30d"),
                "change_1d": p.get("change_1d"),
                "change_7d": p.get("change_7d"),
                "change_30d": p.get("change_30d"),
                "category": p.get("category"),
                "chains": p.get("chains", []),
            })
        ])

async def run_defillama_ingestion(conn):
    """Full DefiLlama ingestion cycle."""
    print("[defillama] Fetching protocols...")
    protocols = await fetch_protocols()
    store_protocols(conn, protocols)
    print(f"[defillama] Stored {len(protocols)} protocols")

    print("[defillama] Fetching fees...")
    fees = await fetch_fees_overview()
    store_fees(conn, fees)
    print(f"[defillama] Stored fees data")

    print("[defillama] Fetching yields...")
    yields = await fetch_yields()
    for y in yields:
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'defillama', 'yield_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"defillama-yield-{y.get('pool', 'unknown')}",
            y.get("project", "unknown"),
            json.dumps({
                "pool": y.get("pool"),
                "chain": y.get("chain"),
                "symbol": y.get("symbol"),
                "tvlUsd": y.get("tvlUsd"),
                "apy": y.get("apy"),
                "apyBase": y.get("apyBase"),
                "apyReward": y.get("apyReward"),
                "apyMean30d": y.get("apyMean30d"),
                "stablecoin": y.get("stablecoin"),
                "ilRisk": y.get("ilRisk"),
            })
        ])
    print(f"[defillama] Stored {len(yields)} yield pools")

    print("[defillama] Fetching raises...")
    raises = await fetch_raises()
    if raises:
        for r in raises[:200]:  # Cap at recent
            conn.execute("""
                INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
                VALUES (?, ?, 'defillama', 'raise', ?, CURRENT_TIMESTAMP)
            """, [
                f"defillama-raise-{r.get('name', 'unknown')}-{r.get('date', 'unknown')}",
                r.get("name", "unknown").lower().replace(" ", "-"),
                json.dumps({
                    "name": r.get("name"),
                    "amount": r.get("amount"),
                    "round": r.get("round"),
                    "valuation": r.get("valuation"),
                    "date": r.get("date"),
                    "leadInvestors": r.get("leadInvestors"),
                    "otherInvestors": r.get("otherInvestors"),
                    "chains": r.get("chains", []),
                })
            ])
        print(f"[defillama] Stored {min(len(raises), 200)} raises")

    return {"protocols": len(protocols), "fees": True, "yields": len(yields), "raises": len(raises) if raises else 0}

if __name__ == "__main__":
    import asyncio
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)
    result = asyncio.run(run_defillama_ingestion(conn))
    print(f"[defillama] Done: {result}")
    conn.close()
