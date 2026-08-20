"""Bittensor emission tracking — subsidy intensity analysis.

The key insight from alpha4: token emissions ≠ revenue.
We track emission rates and compare against external revenue to measure subsidy intensity.
"""
from __future__ import annotations
import httpx
from typing import Any
from datetime import datetime

TIMEOUT = httpx.Timeout(15.0)

async def fetch_tao_price() -> float | None:
    """Get current TAO price from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bittensor", "vs_currencies": "usd"},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("bittensor", {}).get("usd")
    except Exception:
        return None

async def fetch_tao_market_data() -> dict[str, Any]:
    """Get TAO market data from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                "https://api.coingecko.com/api/v3/coins/bittensor",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
            r.raise_for_status()
            data = r.json()
            md = data.get("market_data", {})
            return {
                "price_usd": md.get("current_price", {}).get("usd"),
                "market_cap": md.get("market_cap", {}).get("usd"),
                "fdv": md.get("fully_diluted_valuation", {}).get("usd"),
                "circulating_supply": md.get("circulating_supply"),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
                "volume_24h": md.get("total_volume", {}).get("usd"),
                "price_change_24h_pct": md.get("price_change_percentage_24h"),
                "price_change_7d_pct": md.get("price_change_percentage_7d"),
                "price_change_30d_pct": md.get("price_change_percentage_30d"),
            }
    except Exception:
        return {}

async def fetch_subnet_emissions_from_defillama() -> dict[str, Any]:
    """Get Bittensor-related fee/revenue data from DefiLlama."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get("https://api.llama.fi/summary/fees/bittensor?dataType=dailyFees")
            if r.status_code == 200:
                data = r.json()
                return {
                    "daily_fees": data.get("total24h"),
                    "daily_revenue": data.get("total24h"),  # protocol revenue
                    "monthly_fees": data.get("total30d"),
                }
    except Exception:
        pass
    return {}

def calculate_subsidy_intensity(
    emission_tao_per_day: float,
    tao_price: float,
    external_revenue_usd_annual: float | None,
) -> dict[str, Any]:
    """Calculate subsidy intensity — emissions vs external revenue.

    This is the core metric from alpha4: how much token incentive
    is attached to each dollar of real commercial revenue.
    """
    emission_usd_per_day = emission_tao_per_day * tao_price
    emission_usd_annual = emission_usd_per_day * 365

    result: dict[str, Any] = {
        "emission_tao_per_day": emission_tao_per_day,
        "emission_usd_per_day": round(emission_usd_per_day, 2),
        "emission_usd_annual": round(emission_usd_annual, 2),
    }

    if external_revenue_usd_annual and external_revenue_usd_annual > 0:
        ratio = emission_usd_annual / external_revenue_usd_annual
        result["subsidy_ratio"] = round(ratio, 2)
        result["external_revenue_usd_annual"] = external_revenue_usd_annual
        result["verdict"] = (
            "heavily_subsidized" if ratio > 10
            else "moderately_subsidized" if ratio > 3
            else "approaching_sustainability" if ratio > 1
            else "revenue_exceeds_emissions"
        )
    else:
        result["subsidy_ratio"] = None
        result["verdict"] = "external_revenue_unknown"

    return result
