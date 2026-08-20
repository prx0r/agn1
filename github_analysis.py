"""GitHub developer activity analyzer — measures real dev health, not vanity metrics."""
import httpx, json, time
from pathlib import Path
from datetime import datetime, timedelta

HEADERS = {"Accept": "application/vnd.github.v3+json"}
TIMEOUT = 10

def fetch_commits(repo: str, days: int = 30) -> list:
    """Fetch recent commits."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    r = httpx.get(
        f"https://api.github.com/repos/{repo}/commits",
        params={"since": since, "per_page": 100},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json()
    return []

def fetch_contributors(repo: str) -> list:
    """Fetch contributors."""
    r = httpx.get(
        f"https://api.github.com/repos/{repo}/contributors",
        params={"per_page": 100},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json()
    return []

def fetch_releases(repo: str) -> list:
    """Fetch recent releases."""
    r = httpx.get(
        f"https://api.github.com/repos/{repo}/releases",
        params={"per_page": 10},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json()
    return []

def fetch_pull_requests(repo: str, state: str = "all") -> list:
    """Fetch recent PRs."""
    r = httpx.get(
        f"https://api.github.com/repos/{repo}/pulls",
        params={"state": state, "per_page": 100, "sort": "updated"},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json()
    return []

def analyze_repo(repo: str, ticker: str) -> dict:
    """Full analysis of one repo."""
    print(f"  Analyzing {repo}...")
    
    # Basic info
    r = httpx.get(f"https://api.github.com/repos/{repo}", headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"error": f"Could not fetch repo: {r.status_code}"}
    
    info = r.json()
    
    # Commits
    commits_30d = fetch_commits(repo, 30)
    commits_90d = fetch_commits(repo, 90)
    time.sleep(0.3)
    
    # Contributors
    contributors = fetch_contributors(repo)
    time.sleep(0.3)
    
    # Releases
    releases = fetch_releases(repo)
    time.sleep(0.3)
    
    # PRs
    prs = fetch_pull_requests(repo)
    time.sleep(0.3)
    
    # Analysis
    commit_authors_30d = set(c.get("commit", {}).get("author", {}).get("name", "") for c in commits_30d)
    commit_authors_30d.discard("")
    
    # Bus factor: % of commits by top contributor
    author_counts = {}
    for c in commits_30d:
        author = c.get("commit", {}).get("author", {}).get("name", "")
        if author:
            author_counts[author] = author_counts.get(author, 0) + 1
    
    total_commits_30d = len(commits_30d)
    top_author_pct = 0
    if total_commits_30d > 0 and author_counts:
        top_author = max(author_counts.values())
        top_author_pct = top_author / total_commits_30d * 100
    
    # Release velocity
    recent_releases = [r for r in releases if r.get("published_at", "") > (datetime.utcnow() - timedelta(days=90)).isoformat()]
    
    # PR activity
    merged_prs = [p for p in prs if p.get("merged_at")]
    open_prs = [p for p in prs if p.get("state") == "open"]
    
    # External contributors (not in org)
    external_contributors = len([c for c in contributors if c.get("type") == "User"])
    
    result = {
        "repo": repo,
        "ticker": ticker,
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "open_issues": info.get("open_issues_count", 0),
        "language": info.get("language"),
        "created": (info.get("created_at") or "")[:10],
        "pushed": (info.get("pushed_at") or "")[:10],
        
        # Commit activity
        "commits_30d": total_commits_30d,
        "commits_90d": len(commits_90d),
        "unique_authors_30d": len(commit_authors_30d),
        "top_author_pct": round(top_author_pct, 1),
        
        # Bus factor (lower is better — less concentration)
        "bus_factor_risk": "HIGH" if top_author_pct > 80 else "MEDIUM" if top_author_pct > 50 else "LOW",
        
        # Contributors
        "total_contributors": len(contributors),
        
        # Releases
        "releases_90d": len(recent_releases),
        "latest_release": releases[0].get("tag_name") if releases else None,
        
        # PRs
        "merged_prs": len(merged_prs),
        "open_prs": len(open_prs),
        
        # Scores
        "health_score": 0,
    }
    
    # Calculate health score (0-100)
    score = 0
    
    # Commit activity (30 points)
    if total_commits_30d > 50:
        score += 30
    elif total_commits_30d > 20:
        score += 20
    elif total_commits_30d > 5:
        score += 10
    
    # Contributor diversity (20 points)
    if len(commit_authors_30d) > 10:
        score += 20
    elif len(commit_authors_30d) > 5:
        score += 15
    elif len(commit_authors_30d) > 2:
        score += 10
    
    # Bus factor (15 points)
    if top_author_pct < 30:
        score += 15
    elif top_author_pct < 50:
        score += 10
    elif top_author_pct < 70:
        score += 5
    
    # Release velocity (15 points)
    if len(recent_releases) > 3:
        score += 15
    elif len(recent_releases) > 1:
        score += 10
    
    # PR activity (10 points)
    if len(merged_prs) > 20:
        score += 10
    elif len(merged_prs) > 5:
        score += 5
    
    # Recency (10 points)
    pushed = info.get("pushed_at", "")
    if pushed:
        pushed_date = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        days_since = (datetime.now(pushed_date.tzinfo) - pushed_date).days
        if days_since < 7:
            score += 10
        elif days_since < 30:
            score += 5
        elif days_since < 90:
            score += 2
    
    result["health_score"] = min(score, 100)
    
    return result

def main():
    wl = json.loads(Path("watchlist.json").read_text())
    
    results = []
    for t, p in wl["projects"].items():
        repo = p.get("github")
        if repo:
            result = analyze_repo(repo, t)
            results.append(result)
            time.sleep(1)
    
    # Sort by health score
    results.sort(key=lambda x: x.get("health_score", 0), reverse=True)
    
    # Print results
    print(f"\n{'Ticker':10} {'Score':>6} {'Stars':>6} {'Commits':>8} {'Authors':>8} {'Bus%':>6} {'Releases':>9} {'Language':12}")
    print("-" * 80)
    for r in results:
        if "error" not in r:
            print(f"{r['ticker']:10} {r['health_score']:>6} {r['stars']:>6} {r['commits_30d']:>8} {r['unique_authors_30d']:>8} {r['top_author_pct']:>5.1f}% {r['releases_90d']:>9} {r['language'] or '':12}")
    
    # Save
    Path("data/github_analysis.json").write_text(json.dumps(results, indent=2))
    print(f"\nSaved to data/github_analysis.json")

if __name__ == "__main__":
    main()
