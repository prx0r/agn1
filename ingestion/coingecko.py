"""CoinGecko ingestion — free keyless API."""
from __future__ import annotations
import httpx
import json
import time
from typing import Any

TIMEOUT = httpx.Timeout(30.0)
BASE = "https://api.coingecko.com/api/v3"

async def fetch_top_coins(limit: int = 250) -> list[dict]:
    """Top coins by market cap."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d",
        })
        if r.status_code == 429:
            print("[coingecko] Rate limited, waiting 60s...")
            time.sleep(60)
            return []
        r.raise_for_status()
        return r.json()

async def fetch_category(category: str) -> list[dict]:
    """Coins in a category."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/coins/markets", params={
            "vs_currency": "usd",
            "category": category,
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
        })
        if r.status_code == 429:
            time.sleep(60)
            return []
        r.raise_for_status()
        return r.json()

async def fetch_coin_detail(coin_id: str) -> dict:
    """Detailed coin data."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/coins/{coin_id}", params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false",
        })
        if r.status_code == 429:
            time.sleep(60)
            return {}
        r.raise_for_status()
        return r.json()

async def fetch_trending() -> list[dict]:
    """Trending coins."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{BASE}/search/trending")
        if r.status_code == 429:
            return []
        r.raise_for_status()
        return r.json().get("coins", [])

def store_coins(conn, coins: list[dict]):
    """Store coin data into DuckDB."""
    for coin in coins:
        coin_id = coin.get("id", "")
        symbol = coin.get("symbol", "").upper()

        # Price snapshot
        conn.execute("""
            INSERT OR REPLACE INTO price_snapshots
            (project_id, timestamp, price, mcap, fdv, volume_24h, holders)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """, [
            coin_id,
            coin.get("current_price"),
            coin.get("market_cap"),
            coin.get("fully_diluted_valuation"),
            coin.get("total_volume"),
            coin.get("total_supply"),  # Placeholder — CoinGecko doesn't give holders in market endpoint
        ])

        # Upsert project
        conn.execute("""
            INSERT OR REPLACE INTO projects (id, name, ticker, mcap, fdv, last_updated)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                mcap = excluded.mcap,
                fdv = excluded.fdv,
                last_updated = CURRENT_TIMESTAMP
        """, [
            coin_id,
            coin.get("name"),
            symbol,
            coin.get("market_cap"),
            coin.get("fully_diluted_valuation"),
        ])

        # Observation
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'coingecko', 'market_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"cg-{coin_id}",
            coin_id,
            json.dumps({
                "price": coin.get("current_price"),
                "mcap": coin.get("market_cap"),
                "fdv": coin.get("fully_diluted_valuation"),
                "volume_24h": coin.get("total_volume"),
                "price_change_24h": coin.get("price_change_percentage_24h"),
                "price_change_7d": coin.get("price_change_percentage_7d"),
                "price_change_30d": coin.get("price_change_percentage_30d"),
                "ath": coin.get("ath"),
                "ath_change_percentage": coin.get("ath_change_percentage"),
                "atl": coin.get("atl"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "categories": coin.get("categories", []),
            })
        ])

def store_coin_detail(conn, coin_id: str, detail: dict):
    """Store detailed coin data including developer/community info."""
    dev = detail.get("developer_data", {})
    community = detail.get("community_data", {})

    if dev:
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'coingecko', 'dev_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"cg-dev-{coin_id}",
            coin_id,
            json.dumps({
                "github_repos": dev.get("forks"),
                "github_stars": dev.get("stars"),
                "github_subscribers": dev.get("subscribers"),
                "github_total_issues": dev.get("total_issues"),
                "github_closed_issues": dev.get("closed_issues"),
                "github_pull_requests_merged": dev.get("pull_requests_merged"),
                "github_pull_request_contributors": dev.get("pull_request_contributors"),
                "commit_count_4_weeks": dev.get("commit_count_4_weeks"),
                "code_additions_4_weeks": dev.get("code_additions_deletions_4_weeks", {}).get("additions"),
                "code_deletions_4_weeks": dev.get("code_additions_deletions_4_weeks", {}).get("deletions"),
            })
        ])

    if community:
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'coingecko', 'community_snapshot', ?, CURRENT_TIMESTAMP)
        """, [
            f"cg-community-{coin_id}",
            coin_id,
            json.dumps({
                "twitter_followers": community.get("twitter_followers"),
                "reddit_subscribers": community.get("reddit_subscribers"),
                "reddit_active_accounts": community.get("reddit_accounts_active_48h"),
                "telegram_members": community.get("telegram_channel_user_count"),
                "facebook_likes": community.get("facebook_likes"),
            })
        ])

async def run_coingecko_ingestion(conn, target_projects: list[str] | None = None):
    """Full CoinGecko ingestion cycle."""
    print("[coingecko] Fetching top coins...")
    coins = await fetch_top_coins(250)
    store_coins(conn, coins)
    print(f"[coingecko] Stored {len(coins)} coins")

    # Fetch details for specific projects we care about
    if target_projects:
        for project_id in target_projects:
            print(f"[coingecko] Fetching details for {project_id}...")
            detail = await fetch_coin_detail(project_id)
            if detail:
                store_coin_detail(conn, project_id, detail)
            time.sleep(1.5)  # Rate limit

    print("[coingecko] Fetching trending...")
    trending = await fetch_trending()
    print(f"[coingecko] {len(trending)} trending coins")

    return {"coins": len(coins), "trending": len(trending)}

if __name__ == "__main__":
    import asyncio
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)

    # Target our thesis projects
    targets = [
        "phala-network", "autonolas", "peaq", "nuet", "fluence",
        "lagrange", "zkpass", "openledger", "auki-labs", "flock",
        "brevis", "hivemapper", "vana", "sahara-ai",
    ]
    result = asyncio.run(run_coingecko_ingestion(conn, targets))
    print(f"[coingecko] Done: {result}")
    conn.close()
