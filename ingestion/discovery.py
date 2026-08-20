"""Discovery pipeline — find new projects before CoinGecko."""
from __future__ import annotations
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import Any

TIMEOUT = httpx.Timeout(30.0)

# GitHub search queries for thesis vocabulary
DISCOVERY_QUERIES = [
    '"ERC-8004" "TEE"',
    '"ERC-8004" "x402"',
    '"x402" "MCP"',
    '"x402" "attestation"',
    '"A2A" "payment" agent',
    '"agent" "remote attestation"',
    '"agent" "TDX"',
    '"agent" "SEV-SNP"',
    '"agent" "zkTLS"',
    '"agent" "zkML"',
    '"agent" "provenance"',
    '"agent wallet" "policy"',
    '"agent" "delegation"',
    '"agent" "receipt"',
    '"machine" "ERC-8004"',
    '"robot" "x402"',
    '"verifiable inference" crypto',
    '"proof of inference"',
    '"confidential compute" agent',
    '"proof market"',
]

async def search_github_repos(query: str, sort: str = "stars", limit: int = 10) -> list[dict]:
    """Search GitHub for repos matching a query."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get("https://api.github.com/search/repositories", params={
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": limit,
        }, headers={"Accept": "application/vnd.github.v3+json"})
        if r.status_code == 403:
            print(f"[discovery] Rate limited on query: {query}")
            return []
        if r.status_code != 200:
            return []
        return r.json().get("items", [])

async def check_erc8004_registry() -> list[dict]:
    """Check ERC-8004 registry for new agent registrations."""
    # This would query the on-chain registry — stub for now
    # In production, query Ethereum/BSC/Base for ERC8004 events
    return []

async def check_ethglobal_showcase() -> list[dict]:
    """Scrape ETHGlobal showcase for relevant projects."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get("https://ethglobal.com/api/showcase")
        if r.status_code == 200:
            projects = r.json()
            # Filter for agent/attestation/proof related
            relevant = []
            for p in projects:
                tags = " ".join(p.get("tags", [])).lower()
                desc = (p.get("description", "") + " " + p.get("pitch", "")).lower()
                keywords = ["agent", "attestation", "tee", "proof", "x402", "erc-8004", "reputation", "verifiable"]
                if any(kw in tags or kw in desc for kw in keywords):
                    relevant.append({
                        "name": p.get("name"),
                        "description": p.get("description"),
                        "url": p.get("url"),
                        "tags": p.get("tags"),
                        "source": "ethglobal",
                    })
            return relevant
    return []

async def discover_repos(queries: list[str] | None = None) -> list[dict]:
    """Run discovery queries against GitHub."""
    if queries is None:
        queries = DISCOVERY_QUERIES

    all_results = []
    seen = set()

    for query in queries:
        print(f"[discovery] Searching: {query}")
        repos = await search_github_repos(query, limit=5)
        for repo in repos:
            full_name = repo.get("full_name", "")
            if full_name not in seen:
                seen.add(full_name)
                all_results.append({
                    "repo": full_name,
                    "stars": repo.get("stargazers_count"),
                    "description": repo.get("description"),
                    "language": repo.get("language"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "url": repo.get("html_url"),
                    "topics": repo.get("topics", []),
                    "query": query,
                })
        time.sleep(2)  # Rate limit

    return all_results

def classify_project(repos: list[dict]) -> dict[str, Any]:
    """Classify discovered repos by thesis category."""
    categories = {
        "identity": [],
        "execution": [],
        "payments": [],
        "proof": [],
        "data": [],
        "physical": [],
        "agent_economy": [],
    }

    for repo in repos:
        topics = " ".join(repo.get("topics", [])).lower()
        desc = (repo.get("description", "") or "").lower()
        text = topics + " " + desc

        if any(kw in text for kw in ["erc-8004", "agent identity", "agent passport", "reputation"]):
            categories["identity"].append(repo)
        if any(kw in text for kw in ["tee", "tdx", "sgx", "confidential", "attestation"]):
            categories["execution"].append(repo)
        if any(kw in text for kw in ["x402", "payment", "settlement", "escrow"]):
            categories["payments"].append(repo)
        if any(kw in text for kw in ["zkml", "zk proof", "verifiable", "proof market"]):
            categories["proof"].append(repo)
        if any(kw in text for kw in ["zktls", "provenance", "data", "oracle"]):
            categories["data"].append(repo)
        if any(kw in text for kw in ["robot", "machine", "physical", "spatial", "iot"]):
            categories["physical"].append(repo)
        if any(kw in text for kw in ["agent", "a2a", "swarm", "marketplace", "hire"]):
            categories["agent_economy"].append(repo)

    return {k: v for k, v in categories.items() if v}

async def run_discovery(conn):
    """Full discovery cycle."""
    print("[discovery] Running GitHub repo discovery...")
    repos = await discover_repos()
    print(f"[discovery] Found {len(repos)} unique repos")

    # Store discoveries
    for repo in repos:
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'discovery', 'github_discovery', ?, CURRENT_TIMESTAMP)
        """, [
            f"discovery-{repo['repo'].replace('/', '-')}",
            repo['repo'].split('/')[-1].lower(),
            json.dumps(repo),
        ])

    # Classify
    categories = classify_project(repos)
    print("[discovery] Categories:")
    for cat, items in categories.items():
        print(f"  {cat}: {len(items)} repos")

    # Check ETHGlobal
    print("[discovery] Checking ETHGlobal showcase...")
    ethglobal = await check_ethglobal_showcase()
    print(f"[discovery] Found {len(ethglobal)} relevant ETHGlobal projects")

    for proj in ethglobal:
        conn.execute("""
            INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
            VALUES (?, ?, 'discovery', 'ethglobal_project', ?, CURRENT_TIMESTAMP)
        """, [
            f"ethglobal-{proj['name'].lower().replace(' ', '-')}",
            proj['name'].lower().replace(' ', '-'),
            json.dumps(proj),
        ])

    return {"repos": len(repos), "categories": {k: len(v) for k, v in categories.items()}, "ethglobal": len(ethglobal)}

if __name__ == "__main__":
    import asyncio
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)
    result = asyncio.run(run_discovery(conn))
    print(f"[discovery] Done: {result}")
    conn.close()
