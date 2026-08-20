"""Sync watchlist.json entities into the graph. Run after sync_schema.py."""
import json, httpx
from pathlib import Path

KEY = 'sk_live_gn4kbbvEcLwd.ThYBBADOGCFxGAWUqFWpLjupir6pcbxJmqz3xdWlfLk'
BASE = 'https://api.hydradb.com/byog/query'
HEADERS = {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'}
DB = 'frontier-graph'
COLLECTION = 'projects'

def run_cypher(query, params=None):
    body = {"database": DB, "collection": COLLECTION, "query": query}
    if params:
        body["params"] = params
    r = httpx.post(BASE, headers=HEADERS, json=body, timeout=30)
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return None
    return r.json().get("data", [])

def sync():
    wl = json.loads(Path("watchlist.json").read_text())

    # Projects
    projects = []
    for t, p in wl["projects"].items():
        projects.append({
            "ticker": t,
            "name": p["name"],
            "category": p["category"],
            "tier": p["tier"],
            "thesis": p["thesis"],
        })

    run_cypher("""
        UNWIND $rows AS row
        MERGE (p:Project {ticker: row.ticker})
        SET p.name = row.name, p.category = row.category,
            p.tier = row.tier, p.thesis = row.thesis
    """, {"rows": projects})
    print(f"Projects: {len(projects)}")

    # Categories
    cats = list(set(p["category"] for p in wl["projects"].values()))
    run_cypher("""
        UNWIND $rows AS row
        MERGE (c:Category {name: row.name})
    """, {"rows": [{"name": c} for c in cats]})
    print(f"Categories: {len(cats)}")

    # Link projects to categories
    run_cypher("""
        MATCH (p:Project), (c:Category)
        WHERE p.category = c.name
        MERGE (p)-[:IN_CATEGORY]->(c)
    """)
    print("Linked projects → categories")

    # Bittensor subnets
    subnets = []
    for netuid, s in wl["bittensor_subnets"].items():
        subnets.append({
            "netuid": int(netuid),
            "name": s["name"],
            "category": s["category"],
        })

    run_cypher("""
        UNWIND $rows AS row
        MERGE (s:BittensorSubnet {netuid: row.netuid})
        SET s.name = row.name, s.category = row.category
    """, {"rows": subnets})
    print(f"Subnets: {len(subnets)}")

    # Link subnets to categories
    run_cypher("""
        MATCH (s:BittensorSubnet), (c:Category)
        WHERE s.category = c.name
        MERGE (s)-[:IN_CATEGORY]->(c)
    """)
    print("Linked subnets → categories")

    # Stats
    stats = run_cypher("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
    """)
    print("\n=== Graph stats ===")
    for row in (stats or []):
        print(f"  {row['label']}: {row['count']}")

if __name__ == "__main__":
    sync()
