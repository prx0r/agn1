"""Fetch live prices for all watchlist projects. Run periodically."""
import httpx, json, time
from pathlib import Path
from datetime import datetime

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
STATE_FILE = Path("data/state.json")
PRICE_LOG = Path("data/prices.jsonl")

# Rate limit: ~30 req/min for CoinGecko free tier
# We batch 20 IDs per request, so ~2 batches for 40 projects
BATCH_SIZE = 20

def load_watchlist():
    return json.loads(Path("watchlist.json").read_text())

def fetch_prices(ids: list[str]) -> dict:
    """Fetch prices for a batch of CoinGecko IDs."""
    batch_str = ",".join(ids)
    r = httpx.get(
        f"{COINGECKO_BASE}/simple/price",
        params={
            "ids": batch_str,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
        },
        timeout=15,
    )
    if r.status_code == 429:
        print("  Rate limited, waiting 60s...")
        time.sleep(60)
        return fetch_prices(ids)
    r.raise_for_status()
    return r.json()

def fetch_all_prices():
    """Fetch prices for all watchlist projects."""
    wl = load_watchlist()
    
    # Collect all CoinGecko IDs
    id_map = {}
    for ticker, p in wl["projects"].items():
        cg_id = p.get("coingecko_id")
        if cg_id:
            id_map[cg_id] = ticker
    
    # Batch fetch
    all_ids = list(id_map.keys())
    all_prices = {}
    
    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i:i+BATCH_SIZE]
        print(f"  Fetching batch {i//BATCH_SIZE + 1}: {len(batch)} ids...")
        data = fetch_prices(batch)
        for cg_id, info in data.items():
            ticker = id_map.get(cg_id, cg_id)
            all_prices[ticker] = {
                "price_usd": info.get("usd", 0),
                "market_cap": info.get("usd_market_cap", 0),
                "volume_24h": info.get("usd_24h_vol", 0),
                "change_24h_pct": info.get("usd_24h_change", 0),
                "coingecko_id": cg_id,
                "fetched_at": datetime.utcnow().isoformat(),
            }
        if i + BATCH_SIZE < len(all_ids):
            time.sleep(2)  # Rate limit courtesy
    
    return all_prices

def save_prices(prices: dict):
    """Save prices to state.json and append to prices.jsonl."""
    # Load existing state
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    
    # Update
    state["prices"] = prices
    state["last_price_fetch"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))
    
    # Append to log
    PRICE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PRICE_LOG, "a") as f:
        for ticker, data in prices.items():
            log_entry = {"ticker": ticker, **data}
            f.write(json.dumps(log_entry) + "\n")
    
    print(f"  Saved {len(prices)} prices to state.json + prices.jsonl")

def print_summary(prices: dict):
    """Print a summary table."""
    print(f"\n{'Ticker':10} {'Price':>12} {'MCap':>10} {'Vol24h':>10} {'24h%':>8}")
    print("-" * 55)
    
    sorted_prices = sorted(prices.items(), key=lambda x: x[1].get("market_cap", 0) or 0, reverse=True)
    for ticker, data in sorted_prices:
        price = data.get("price_usd", 0)
        mcap = data.get("market_cap", 0)
        vol = data.get("volume_24h", 0)
        change = data.get("change_24h_pct", 0)
        
        mcap_str = f"${mcap/1e6:.1f}M" if mcap else "—"
        vol_str = f"${vol/1e6:.1f}M" if vol else "—"
        change_str = f"{change:+.1f}%" if change else "—"
        
        print(f"{ticker:10} ${price:>10.6f} {mcap_str:>10} {vol_str:>10} {change_str:>8}")

if __name__ == "__main__":
    print("Fetching prices...")
    prices = fetch_all_prices()
    save_prices(prices)
    print_summary(prices)
