"""Entity resolution — link projects to repos, contracts, teams, tokens."""
from __future__ import annotations
import json
from typing import Any

# Known project → repo mappings (extendable)
ENTITY_MAP = {
    "phala-network": {
        "ticker": "PHA",
        "github_org": "Phala-Network",
        "repos": ["phala-blockchain", "phala-cloud", "dcap-qvl", "dstack"],
        "chain": "ethereum",
        "contracts": {"ethereum": "0x6c5bE8E3a52054C16c2e7B4E8C6B8d52F8d52f4E"},
        "category": "verifiable_execution",
    },
    "autonolas": {
        "ticker": "OLAS",
        "github_org": "valory-xyz",
        "repos": ["autonolas"],
        "chain": "ethereum",
        "category": "agent_economy",
    },
    "peaq": {
        "ticker": "PEAQ",
        "github_org": "peaqnetwork",
        "repos": ["peaq-sdk"],
        "chain": "peaq",
        "category": "physical_machines",
    },
    "lagrange": {
        "ticker": "LA",
        "github_org": "Lagrange-Labs",
        "repos": ["deep-prove"],
        "chain": "ethereum",
        "category": "proof_generation",
    },
    "zkpass": {
        "ticker": "ZKP",
        "github_org": "zkPassOfficial",
        "repos": ["Transgate-JS-SDK"],
        "chain": "ethereum",
        "category": "data_proofs",
    },
    "openledger": {
        "ticker": "OPEN",
        "github_org": "openledger-ai",
        "repos": [],
        "chain": "ethereum",
        "category": "provenance",
    },
    "auki-labs": {
        "ticker": "AUKI",
        "github_org": "aukilabs",
        "repos": ["posemesh", "reconstruction-server"],
        "chain": "base",
        "category": "physical_ai",
    },
    "flock": {
        "ticker": "FLOCK",
        "github_org": None,  # Closed source
        "repos": [],
        "chain": "base",
        "category": "decentralized_training",
    },
    "brevis": {
        "ticker": "BREV",
        "github_org": "brevis-network",
        "repos": ["pico", "brevis-sdk"],
        "chain": "ethereum",
        "category": "proof_generation",
    },
    "hivemapper": {
        "ticker": "HONEY",
        "github_org": "Hivemapper",
        "repos": ["hive-py"],
        "chain": "solana",
        "category": "physical_ai",
    },
    "vana": {
        "ticker": "VANA",
        "github_org": "vana-com",
        "repos": ["personal-server", "vana-smart-contracts"],
        "chain": "ethereum",
        "category": "data_provenance",
    },
    "sahara-ai": {
        "ticker": "SAHARA",
        "github_org": None,
        "repos": [],
        "chain": "base",
        "category": "data_provenance",
    },
    "nuet": {
        "ticker": "NTX",
        "github_org": "Acurast",  # Verify
        "repos": [],
        "chain": "ethereum",
        "category": "compute_orchestration",
    },
    "fluence": {
        "ticker": "FLT",
        "github_org": "fluencelabs",
        "repos": [],
        "chain": "ethereum",
        "category": "decentralized_compute",
    },
    "acurast": {
        "ticker": "ACU",
        "github_org": "Acurast",
        "repos": ["acurast-cli", "acurast-substrate"],
        "chain": "multiple",
        "category": "attested_compute",
    },
}

def resolve_entity(project_id: str, observations: list[dict]) -> dict[str, Any]:
    """Resolve all known data about a project from observations."""
    entity = ENTITY_MAP.get(project_id, {})
    resolved = {
        "id": project_id,
        "ticker": entity.get("ticker"),
        "category": entity.get("category"),
        "github_org": entity.get("github_org"),
        "repos": entity.get("repos", []),
        "chain": entity.get("chain"),
        "observations": [],
    }

    for obs in observations:
        data = json.loads(obs.get("data", "{}")) if isinstance(obs.get("data"), str) else obs.get("data", {})
        resolved["observations"].append({
            "source": obs.get("source"),
            "type": obs.get("event_type"),
            "data": data,
            "timestamp": obs.get("observed_at"),
        })

    return resolved

def build_entity_graph(conn) -> dict[str, Any]:
    """Build the full entity graph from all stored data."""
    graph = {"projects": {}, "edges": []}

    for project_id in ENTITY_MAP:
        # Get all observations for this project
        rows = conn.execute("""
            SELECT * FROM observations WHERE project_id = ?
            ORDER BY observed_at DESC
        """, [project_id]).fetchall()

        cols = [desc[0] for desc in conn.description] if hasattr(conn, 'description') else []
        observations = [dict(zip(cols, row)) for row in rows] if cols else []

        entity = resolve_entity(project_id, observations)
        graph["projects"][project_id] = entity

        # Build edges
        if entity.get("github_org"):
            graph["edges"].append({
                "source": project_id,
                "target": entity["github_org"],
                "type": "has_github_org",
            })
        for repo in entity.get("repos", []):
            graph["edges"].append({
                "source": project_id,
                "target": repo,
                "type": "has_repo",
            })

    # Cross-project edges (same category)
    categories = {}
    for pid, entity in graph["projects"].items():
        cat = entity.get("category")
        if cat:
            categories.setdefault(cat, []).append(pid)

    for cat, members in categories.items():
        for i, a in enumerate(members):
            for b in members[i+1:]:
                graph["edges"].append({
                    "source": a,
                    "target": b,
                    "type": "competes_with",
                    "category": cat,
                })

    return graph

if __name__ == "__main__":
    from ingestion import get_db
    conn = get_db()
    graph = build_entity_graph(conn)
    print(f"Projects: {len(graph['projects'])}")
    print(f"Edges: {len(graph['edges'])}")
    for pid, entity in graph["projects"].items():
        print(f"  {pid}: {entity.get('ticker')} ({entity.get('category')})")
    conn.close()
