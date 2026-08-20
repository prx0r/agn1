"""Bittensor Radar — structured subnet analysis output.

From alpha5: each subnet analyzed as an experiment in incentive-designed machine intelligence.
"""
from __future__ import annotations
import json
from typing import Any
from datetime import datetime

from bittensor.subnets import SUBNET_REGISTRY, Subnet
from bittensor.emissions import calculate_subsidy_intensity


def analyze_subnet(
    subnet: Subnet,
    tao_price: float,
    emission_tao_per_day: float | None = None,
    external_revenue_usd: float | None = None,
    miner_count: int | None = None,
    holder_count: int | None = None,
    market_cap_usd: float | None = None,
    fdv_usd: float | None = None,
) -> dict[str, Any]:
    """Produce structured analysis for one subnet."""

    emission = None
    if emission_tao_per_day:
        emission = calculate_subsidy_intensity(
            emission_tao_per_day=emission_tao_per_day,
            tao_price=tao_price,
            external_revenue_usd_annual=external_revenue_usd or subnet.external_revenue_usd,
        )

    return {
        "netuid": subnet.netuid,
        "name": subnet.name,
        "ticker": subnet.ticker,
        "description": subnet.description,
        "commodity": subnet.commodity,
        "validator_method": subnet.validator_method,
        "anti_cheat": subnet.anti_cheat,
        "thesis_category": subnet.thesis_category,
        "external_revenue_known": subnet.external_revenue_known,
        "external_revenue_usd": subnet.external_revenue_usd or external_revenue_usd,
        "emission": emission,
        "market": {
            "tao_price": tao_price,
            "market_cap_usd": market_cap_usd,
            "fdv_usd": fdv_usd,
            "miner_count": miner_count,
            "holder_count": holder_count,
        },
        "github_repo": subnet.github_repo,
        "website": subnet.website,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def generate_radar(
    tao_price: float,
    subnet_data: dict[int, dict] | None = None,
) -> dict[str, Any]:
    """Generate BITTENSOR RADAR for all tracked subnets.

    subnet_data: optional dict of netuid → extra data (emissions, miners, etc.)
    """
    data = subnet_data or {}
    analyses = []

    for netuid, subnet in SUBNET_REGISTRY.items():
        extra = data.get(netuid, {})
        analysis = analyze_subnet(
            subnet=subnet,
            tao_price=tao_price,
            emission_tao_per_day=extra.get("emission_tao_per_day"),
            external_revenue_usd=extra.get("external_revenue_usd"),
            miner_count=extra.get("miner_count"),
            holder_count=extra.get("holder_count"),
            market_cap_usd=extra.get("market_cap_usd"),
            fdv_usd=extra.get("fdv_usd"),
        )
        analyses.append(analysis)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "tao_price": tao_price,
        "subnet_count": len(analyses),
        "subnets": analyses,
    }


def radar_to_markdown(radar: dict[str, Any]) -> str:
    """Convert radar output to markdown report."""
    lines = []
    lines.append(f"# Bittensor Radar")
    lines.append(f"*Generated: {radar['generated_at']} | TAO: ${radar['tao_price']:.2f}*\n")

    lines.append("| # | Subnet | Commodity | External Rev | Emission/Day | Subsidy Ratio | Verdict |")
    lines.append("|---|--------|-----------|-------------|-------------|---------------|---------|")

    for s in sorted(radar["subnets"], key=lambda x: x.get("emission", {}).get("emission_usd_annual", 0) if x.get("emission") else 0, reverse=True):
        em = s.get("emission", {})
        ext_rev = f"${s['external_revenue_usd']:,.0f}" if s.get("external_revenue_usd") else "—"
        em_day = f"${em.get('emission_usd_per_day', 0):,.0f}" if em else "—"
        ratio = f"{em.get('subsidy_ratio', 0):.1f}×" if em and em.get("subsidy_ratio") is not None else "—"
        verdict = em.get("verdict", "—").replace("_", " ") if em else "—"

        lines.append(
            f"| {s['netuid']} | **{s['name']}** | {s['commodity'][:40]} | "
            f"{ext_rev} | {em_day} | {ratio} | {verdict} |"
        )

    lines.append("")
    lines.append("### Key Insight")
    lines.append("")
    lines.append("External revenue / token emissions ratio is the single most important metric.")
    lines.append("A subnet can have 500% APY, #1 emissions, hundreds of GPUs, and still have almost no external demand.")
    lines.append("")
    lines.append("### Subnet Details\n")

    for s in radar["subnets"]:
        lines.append(f"#### {s['netuid']}. {s['name']}")
        if s.get("ticker"):
            lines.append(f"- **Ticker:** {s['ticker']}")
        lines.append(f"- **Commodity:** {s['commodity']}")
        lines.append(f"- **Validator:** {s['validator_method']}")
        lines.append(f"- **Anti-cheat:** {s['anti_cheat']}")
        lines.append(f"- **Category:** {s['thesis_category']}")
        if s.get("description"):
            lines.append(f"- **Description:** {s['description']}")
        if s.get("external_revenue_usd"):
            lines.append(f"- **External Revenue:** ${s['external_revenue_usd']:,.0f}/yr")
        if s.get("github_repo"):
            lines.append(f"- **GitHub:** {s['github_repo']}")
        lines.append("")

    return "\n".join(lines)
