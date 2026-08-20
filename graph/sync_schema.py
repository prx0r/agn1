"""Sync schema.yaml to HydraDB BYOG graph. Run after editing schema.yaml."""
import yaml, httpx, json, sys
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
    schema = yaml.safe_load(Path("graph/schema.yaml").read_text())

    print("=== Creating indexes ===")
    for label, spec in schema.get("nodes", {}).items():
        for prop in spec.get("indexes", []):
            q = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
            run_cypher(q)
            print(f"  {label}.{prop}")

    print("\n=== Done. Node/relationship types are created on first write. ===")
    print("Use sync_entities.py to load actual data.")

if __name__ == "__main__":
    sync()
