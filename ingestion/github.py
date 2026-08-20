"""GitHub ingestion — clone repos, analyze activity, GH Archive."""
from __future__ import annotations
import subprocess
import json
import os
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

REPOS_DIR = Path(__file__).parent.parent / "data" / "repos"

# Thesis projects and their key repos
THESIS_REPOS = {
    "phala-network": [
        "Phala-Network/phala-blockchain",
        "Phala-Network/phala-cloud",
        "Phala-Network/dcap-qvl",
    ],
    "autonolas": [
        "valory-xyz/autonolas",
    ],
    "peaq": [
        "peaqnetwork/peaq-sdk",
    ],
    "lagrange": [
        "Lagrange-Labs/deep-prove",
    ],
    "zkpass": [
        "zkPassOfficial/Transgate-JS-SDK",
    ],
    "openledger": [
        # Closed source — no repos
    ],
    "auki-labs": [
        "aukilabs/posemesh",
        "aukilabs/reconstruction-server",
    ],
    "flock": [
        # Closed source — no repos
    ],
    "brevis": [
        "brevis-network/pico",
        "brevis-network/brevis-sdk",
    ],
    "hivemapper": [
        "Hivemapper/hive-py",
    ],
    "vana": [
        "vana-com/personal-server",
        "vana-com/vana-smart-contracts",
    ],
}

def clone_repo(repo: str) -> Path | None:
    """Clone a repo if not already cloned."""
    dest = REPOS_DIR / repo.replace("/", "_")
    if dest.exists():
        # Just fetch latest
        try:
            subprocess.run(
                ["git", "-C", str(dest), "fetch", "--quiet"],
                capture_output=True, timeout=30
            )
            return dest
        except Exception:
            return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(dest)],
            capture_output=True, timeout=60
        )
        return dest
    except Exception:
        return None

def analyze_repo(repo_path: Path) -> dict[str, Any]:
    """Analyze a cloned repo for dev activity signals."""
    result = {}

    try:
        # Last commit date
        log = subprocess.run(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%ci"],
            capture_output=True, text=True, timeout=10
        )
        result["last_commit"] = log.stdout.strip()

        # Total commits
        log = subprocess.run(
            ["git", "-C", str(repo_path), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        result["total_commits"] = int(log.stdout.strip()) if log.stdout.strip().isdigit() else 0

        # Unique authors (last 90 days)
        since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        log = subprocess.run(
            ["git", "-C", str(repo_path), "log", f"--since={since}", "--format=%ae"],
            capture_output=True, text=True, timeout=10
        )
        authors = set(a.strip() for a in log.stdout.strip().split("\n") if a.strip())
        # Filter out bots
        bot_patterns = {"dependabot", "renovate", "github-actions", "noreply", "bot@")
        real_authors = {a for a in authors if not any(bp in a.lower() for bp in bot_patterns)}
        result["unique_authors_90d"] = len(real_authors)
        result["authors_90d"] = list(real_authors)[:20]

        # Commits last 30 days
        since_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        log = subprocess.run(
            ["git", "-C", str(repo_path), "log", f"--since={since_30}", "--oneline"],
            capture_output=True, text=True, timeout=10
        )
        result["commits_30d"] = len([l for l in log.stdout.strip().split("\n") if l.strip()])

        # Tags (releases)
        log = subprocess.run(
            ["git", "-C", str(repo_path), "tag", "--sort=-creatordate"],
            capture_output=True, text=True, timeout=10
        )
        tags = [t.strip() for t in log.stdout.strip().split("\n") if t.strip()]
        result["total_tags"] = len(tags)
        result["latest_tag"] = tags[0] if tags else None

        # Bus factor (top contributor share)
        log = subprocess.run(
            ["git", "-C", str(repo_path), "shortlog", "-sn", "--all"],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in log.stdout.strip().split("\n") if l.strip()]
        counts = []
        for line in lines:
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].strip().isdigit():
                counts.append(int(parts[0].strip()))
        total = sum(counts) if counts else 1
        result["bus_factor_top_pct"] = (counts[0] / total * 100) if counts else 100
        result["num_contributors"] = len(counts)

        # Languages
        log = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files"],
            capture_output=True, text=True, timeout=10
        )
        files = log.stdout.strip().split("\n")
        exts = {}
        for f in files:
            ext = Path(f).suffix.lower()
            if ext:
                exts[ext] = exts.get(ext, 0) + 1
        result["file_extensions"] = dict(sorted(exts.items(), key=lambda x: -x[1])[:10])

    except Exception as e:
        result["error"] = str(e)

    return result

def store_repo_analysis(conn, project_id: str, repo_name: str, analysis: dict):
    """Store repo analysis into DuckDB."""
    conn.execute("""
        INSERT OR REPLACE INTO repos (id, project_id, stars, language, last_commit, first_seen)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [
        repo_name,
        project_id,
        analysis.get("total_commits"),  # Using commits as proxy for now
        None,
        analysis.get("last_commit"),
    ])

    conn.execute("""
        INSERT OR REPLACE INTO dev_activity (repo_id, period, unique_authors, commits, measured_at)
        VALUES (?, '90d', ?, ?, CURRENT_TIMESTAMP)
    """, [
        repo_name,
        analysis.get("unique_authors_90d", 0),
        analysis.get("commits_30d", 0),
    ])

    conn.execute("""
        INSERT OR REPLACE INTO observations (id, project_id, source, event_type, data, observed_at)
        VALUES (?, ?, 'github', 'repo_analysis', ?, CURRENT_TIMESTAMP)
    """, [
        f"github-{repo_name}",
        project_id,
        json.dumps(analysis),
    ])

async def run_github_ingestion(conn):
    """Clone and analyze all thesis repos."""
    results = {}
    for project_id, repos in THESIS_REPOS.items():
        if not repos:
            results[project_id] = {"status": "closed_source"}
            continue

        project_results = []
        for repo in repos:
            print(f"[github] Cloning {repo}...")
            path = clone_repo(repo)
            if path:
                print(f"[github] Analyzing {repo}...")
                analysis = analyze_repo(path)
                store_repo_analysis(conn, project_id, repo, analysis)
                project_results.append(analysis)
                print(f"[github] {repo}: {analysis.get('unique_authors_90d', 0)} authors, {analysis.get('commits_30d', 0)} commits/30d")
            else:
                print(f"[github] Failed to clone {repo}")

        results[project_id] = project_results

    return results

if __name__ == "__main__":
    import asyncio
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)
    results = asyncio.run(run_github_ingestion(conn))
    print(f"[github] Done: {list(results.keys())}")
    conn.close()
