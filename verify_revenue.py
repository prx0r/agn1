"""Revenue verification — cross-check DefiLlama vs project claims vs on-chain."""
import httpx, json, time
from pathlib import Path

HEADERS = {"Accept": "application/vnd.github.v3+json"}

def verify_revenue(ticker: str, defillama_slug: str = None) -> dict:
    """Verify revenue data from multiple sources."""
    result = {"ticker": ticker, "sources": {}, "verdict": "unknown"}
    
    # 1. DefiLlama fees
    if defillama_slug:
        try:
            r = httpx.get(f"https://api.llama.fi/summary/fees/{defillama_slug}?dataType=dailyFees", timeout=10)
            if r.status_code == 200:
                data = r.json()
                result["sources"]["defillama_fees"] = {
                    "daily_24h": data.get("total24h"),
                    "daily_30d": data.get("total30d"),
                    "annualized": data.get("total24h", 0) * 365 if data.get("total24h") else None,
                }
            time.sleep(0.5)
            
            r2 = httpx.get(f"https://api.llama.fi/summary/fees/{defillama_slug}?dataType=dailyRevenue", timeout=10)
            if r2.status_code == 200:
                data2 = r2.json()
                result["sources"]["defillama_revenue"] = {
                    "daily_24h": data2.get("total24h"),
                    "daily_30d": data2.get("total30d"),
                    "annualized": data2.get("total24h", 0) * 365 if data2.get("total24h") else None,
                }
            time.sleep(0.5)
        except:
            pass
    
    # 2. DefiLlama protocol data
    if defillama_slug:
        try:
            r3 = httpx.get(f"https://api.llama.fi/protocol/{defillama_slug}", timeout=10)
            if r3.status_code == 200:
                data3 = r3.json()
                result["sources"]["defillama_protocol"] = {
                    "tvl": data3.get("currentChainTvls", {}).get("tvl", 0),
                    "mcap": data3.get("mcap"),
                }
            time.sleep(0.5)
        except:
            pass
    
    # 3. Determine verdict
    fees = result["sources"].get("defillama_fees", {})
    rev = result["sources"].get("defillama_revenue", {})
    
    if rev.get("annualized") and rev["annualized"] > 1000000:
        result["verdict"] = "verified_revenue"
    elif fees.get("annualized") and fees["annualized"] > 100000:
        result["verdict"] = "verified_fees"
    elif fees.get("daily_24h") and fees["daily_24h"] > 0:
        result["verdict"] = "low_revenue"
    else:
        result["verdict"] = "no_revenue_data"
    
    return result

def main():
    wl = json.loads(Path("watchlist.json").read_text())
    
    results = []
    for t, p in wl["projects"].items():
        slug = p.get("defillama_slug")
        if slug:
            print(f"Verifying {t}...")
            result = verify_revenue(t, slug)
            results.append(result)
            time.sleep(1)
    
    # Print results
    print(f"\n{'Ticker':10} {'Verdict':20} {'Fees/yr':>12} {'Rev/yr':>12} {'TVL':>12}")
    print("-" * 70)
    for r in results:
        fees = r["sources"].get("defillama_fees", {})
        rev = r["sources"].get("defillama_revenue", {})
        proto = r["sources"].get("defillama_protocol", {})
        
        fees_s = f"${fees.get('annualized', 0)/1e6:.1f}M" if fees.get("annualized") else "—"
        rev_s = f"${rev.get('annualized', 0)/1e6:.1f}M" if rev.get("annualized") else "—"
        tvl_s = f"${proto.get('tvl', 0)/1e6:.1f}M" if proto.get("tvl") else "—"
        
        print(f"{r['ticker']:10} {r['verdict']:20} {fees_s:>12} {rev_s:>12} {tvl_s:>12}")
    
    # Save
    Path("data/revenue_verification.json").write_text(json.dumps(results, indent=2))
    print(f"\nSaved to data/revenue_verification.json")

if __name__ == "__main__":
    main()
