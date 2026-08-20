"""Sync hierarchical schema to HydraDB BYOG graphs.

Usage:
  python3 sync_schema.py                    # sync all collections
  python3 sync_schema.py projects           # sync only projects collection
  python3 sync_schema.py --dry-run          # show what would be created
"""
import yaml, httpx, json, sys
from pathlib import Path

KEY = 'sk_live_gn4kbbvEcLwd.ThYBBADOGCFxGAWUqFWpLjupir6pcbxJmqz3xdWlfLk'
BASE = 'https://api.hydradb.com/byog/query'
HEADERS = {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'}

# Map collection names to HydraDB database names
COLLECTIONS = {
    'projects': 'frontier-graph',
    'bittensor': 'frontier-graph',  # same database, different collection
    'decisions': 'frontier-graph',
}

def run_cypher(database, collection, query, params=None):
    body = {"database": database, "collection": collection, "query": query}
    if params:
        body["params"] = params
    r = httpx.post(BASE, headers=HEADERS, json=body, timeout=30)
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return None
    return r.json().get("data", [])

def load_parent_schema():
    return yaml.safe_load(Path("graph/schema.yaml").read_text())

def load_collection_schema(collection_name):
    parent = load_parent_schema()
    col_file = parent["collections"][collection_name]["file"]
    col_schema = yaml.safe_load(Path(f"graph/{col_file}").read_text())

    # Merge global + collection-specific
    merged_nodes = {}
    merged_nodes.update(parent.get("global_nodes", {}))
    merged_nodes.update(col_schema.get("nodes", {}))

    merged_rels = {}
    merged_rels.update(parent.get("global_relationships", {}))
    merged_rels.update(col_schema.get("relationships", {}))

    return {"nodes": merged_nodes, "relationships": merged_rels}

def sync_collection(collection_name, dry_run=False):
    database = COLLECTIONS[collection_name]
    schema = load_collection_schema(collection_name)

    print(f"\n=== Syncing {collection_name} (db={database}) ===")

    # Create indexes
    for label, spec in schema.get("nodes", {}).items():
        for prop in spec.get("indexes", []):
            q = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
            if dry_run:
                print(f"  [dry] {label}.{prop}")
            else:
                run_cypher(database, collection_name, q)
                print(f"  {label}.{prop}")

    # Print relationship types (auto-created on first merge)
    for rel_name, rel_spec in schema.get("relationships", {}).items():
        from_types = ", ".join(rel_spec["from"]) if rel_spec["from"] != "*" else "*"
        to_type = rel_spec["to"]
        print(f"  {rel_name}: {from_types} → {to_type}")

def main():
    dry_run = "--dry-run" in sys.argv
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None

    if target:
        sync_collection(target, dry_run)
    else:
        for name in COLLECTIONS:
            sync_collection(name, dry_run)

if __name__ == "__main__":
    main()
