"""Validate data sources for all watchlist projects. Run once to check what works."""
import json
import httpx
from pathlib import Path

TIMEOUT = httpx.Timeout(15.0)

def load_watchlist():
    return json.loads(Path("watchlist.json").read_text())

def test_coingecko(watchlist):
    """Test CoinGecko for all projects."""
    print("\n=== CoinGecko ===")
    ids = []
    id_map = {}
    for ticker, p in watchlist["projects"].items():
        cid = p.get("coingecko_id")
        if cid:
            ids.append(cid)
            id_map[cid] = ticker

    if not ids:
        return

    r = httpx.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": ",".join(ids), "vs_currencies": "usd", "include_market_cap": "true"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        print(f"  ERROR: {r.status_code}")
        return

    data = r.json()
    for cid, ticker in id_map.items():
        info = data.get(cid, {})
        price = info.get("usd", 0)
        mcap = info.get("usd_market_cap", 0)
        print(f"  {ticker}: ${price:,.6f} mcap=${mcap:,.0f}" if mcap else f"  {ticker}: ${price:,.6f} mcap=N/A")

def test_defillama(watchlist):
    """Test DefiLlama for all projects."""
    print("\n=== DefiLlama ===")
    r = httpx.get("https://api.llama.fi/protocols", timeout=30)
    if r.status_code != 200:
        print(f"  ERROR: {r.status_code}")
        return

    protocols = r.json()
    slug_map = {}
    for ticker, p in watchlist["projects"].items():
        slug = p.get("defillama_slug")
        if slug:
            slug_map[slug] = ticker

    found = set()
    for p in protocols:
        slug = p.get("slug", "").lower()
        if slug in slug_map:
            ticker = slug_map[slug]
            found.add(ticker)
            mcap = p.get("mcap") or 0
            tvl = p.get("tvl") or 0
            fees = "has_fees" if any(f in p.get("name", "").lower() for f in ["chutes"]) else ""
            print(f"  {ticker}: mcap=${mcap:,.0f} tvl=${tvl:,.0f} {fees}")

    for ticker, p in watchlist["projects"].items():
        if p.get("defillama_slug") and ticker not in found:
            print(f"  {ticker}: NOT FOUND (slug={p['defillama_slug']})")

def test_github(watchlist):
    """Test GitHub for all projects."""
    print("\n=== GitHub ===")
    for ticker, p in watchlist["projects"].items():
        repo = p.get("github")
        if not repo:
            print(f"  {ticker}: no repo")
            continue
        try:
            r = httpx.get(
                f"https://api.github.com/repos/{repo}",
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if r.status_code == 200:
                d = r.json()
                print(f"  {ticker}: stars={d['stargazers_count']} forks={d['forks_count']} pushed={d['pushed_at'][:10]}")
            else:
                print(f"  {ticker}: {r.status_code}")
        except Exception as e:
            print(f"  {ticker}: ERROR {e}")

def test_defillama_fees(watchlist):
    """Test DefiLlama fees for Chutes."""
    print("\n=== DefiLlama Fees (Chutes) ===")
    r = httpx.get("https://api.llama.fi/summary/fees/chutes?dataType=dailyFees", timeout=15)
    if r.status_code == 200:
        d = r.json()
        print(f"  24h fees: ${d.get('total24h', 0):,.0f}")
        print(f"  30d fees: ${d.get('total30d', 0):,.0f}")
        print(f"  annualized: ${d.get('total24h', 0) * 365:,.0f}")
    else:
        print(f"  ERROR: {r.status_code}")

def test_erc8004():
    """Test ERC-8004 GitHub for new implementations."""
    print("\n=== ERC-8004 GitHub ===")
    r = httpx.get("https://api.github.com/orgs/erc-8004/repos", timeout=10, headers={"Accept": "application/vnd.github.v3+json"})
    if r.status_code == 200:
        for repo in r.json():
            desc = (repo.get("description") or "")[:60]
            print(f"  {repo['name']}: stars={repo['stargazers_count']} {desc}")

def test_x402():
    """Test x402 GitHub."""
    print("\n=== x402 ===")
    r = httpx.get("https://api.github.com/repos/x402-foundation/x402", timeout=10, headers={"Accept": "application/vnd.github.v3+json"})
    if r.status_code == 200:
        d = r.json()
        print(f"  x402-foundation/x402: stars={d['stargazers_count']} forks={d['forks_count']}")

if __name__ == "__main__":
    wl = load_watchlist()
    test_coingecko(wl)
    test_defillama(wl)
    test_github(wl)
    test_defillama_fees(wl)
    test_erc8004()
    test_x402()
