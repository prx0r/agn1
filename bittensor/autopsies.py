"""Incentive mechanism autopsies — deep analysis of how each subnet's incentive design works.

From alpha5: every subnet makes decisions about what gets measured, who measures it,
how miners can game it, and what maximizing rewards actually produces.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class IncentiveMechanism:
    """A structured analysis of one subnet's incentive mechanism."""
    netuid: int
    name: str
    # Core questions
    what_is_measured: str = ""
    who_measures: str = ""
    how_can_miners_game: str = ""
    what_does_maximizing_produce: str = ""
    does_commodity_have_external_demand: str = ""
    # Analysis
    gaming_risks: list[str] = field(default_factory=list)
    concentration_risks: list[str] = field(default_factory=list)
    alignment_notes: str = ""
    # Evidence
    evidence: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


# Pre-populated from research (alpha4, alpha5)
AUTOPSY_REGISTRY: dict[int, IncentiveMechanism] = {
    64: IncentiveMechanism(
        netuid=64,
        name="Chutes",
        what_is_measured="Serverless inference revenue (PAYG, subscriptions, private hosting)",
        who_measures="Revenue verification + TEE attestation",
        how_can_miners_game="Promotional abuse was detected and removed (free quota gaming, subscription abuse up to $6,400 usage on $20 subs)",
        what_does_maximizing_produce="Actual commercial inference revenue — miners who serve paying customers earn more",
        does_commodity_have_external_demand="Yes — $5.33M annualized, measurable via DefiLlama + own API",
        gaming_risks=[
            "Subsidized free traffic can inflate token metrics without revenue",
            "Miner collusion to inflate emission share",
        ],
        concentration_risks=[
            "18% subnet-owner cut",
            "Revenue concentrated among few high-volume miners",
        ],
        alignment_notes="Strong — Chutes intentionally removed ~40B tokens/day of non-revenue traffic, proving alignment between incentive and real value",
        evidence=[
            "DefiLlama shows $5.33M annualized revenue",
            "Revenue per GPU improved $4.05→$5.89 after cleanup",
            "Revenue per million tokens +37.7% after abuse removal",
        ],
        open_questions=[
            "What is the COGS breakdown for miners?",
            "How does emission share compare to revenue share?",
            "What happens when emissions decrease?",
        ],
    ),
    51: IncentiveMechanism(
        netuid=51,
        name="Lium",
        what_is_measured="GPU rental fulfillment — provider gets 95%, platform retains 5%",
        who_measures="Provider pricing + rental completion verification",
        how_can_miners_game="Self-renting between controlled wallets, inflated pricing",
        what_does_maximizing_produce="More GPU supply at lower prices — but does it produce paying customers?",
        does_commodity_have_external_demand="Unknown — no aggregate rental volume disclosed",
        gaming_risks=[
            "Self-renting to capture emissions",
            "Inflated pricing without real demand",
            "No aggregate revenue disclosure makes verification impossible",
        ],
        concentration_risks=[
            "21.88% of all Bittensor emissions — #1 subnet",
            "Emissions may vastly exceed external revenue",
        ],
        alignment_notes="Weak — emission share exceeds what we can verify as external demand",
        evidence=[
            "Clear business model (95/5 split)",
            "Supports H100/H200/B200 + consumer GPUs",
            "No aggregate rental GMV disclosed",
        ],
        open_questions=[
            "What is total rental GMV?",
            "What is the 5% platform fee in USD?",
            "How many unique customers?",
            "Is rental demand growing or flat?",
        ],
    ),
    53: IncentiveMechanism(
        netuid=53,
        name="engy",
        what_is_measured="Verified inference — miners must prove they ran the specified model via TOPLOC activation fingerprints",
        who_measures="Cryptographic commitments + sampled recomputation/auditing",
        how_can_miners_game="Benchmark contamination, activation fingerprint spoofing, model weight manipulation",
        what_does_maximizing_produce="Better verified inference — but only if requests are paid (cost_micro > 0)",
        does_commodity_have_external_demand="Unknown — no aggregate revenue disclosed",
        gaming_risks=[
            "TOPLOC fingerprint spoofing",
            "Using different model than claimed",
            "Sampling gaps in auditing",
        ],
        concentration_risks=[
            "139 miners — relatively decentralized",
            "Emission equivalent ~231 TAO/day",
        ],
        alignment_notes="Interesting — explicitly counts only billed requests (cost_micro > 0), so aligned with paid usage",
        evidence=[
            "Cryptographic model weight commitments",
            "TOPLOC activation fingerprints",
            "Sampled recomputation auditing",
        ],
        open_questions=[
            "What is total billed inference revenue?",
            "How does TOPLOC perform against adversarial miners?",
            "What is the false positive/negative rate of auditing?",
        ],
    ),
    4: IncentiveMechanism(
        netuid=4,
        name="Targon",
        what_is_measured="GPU compute supply — 248+ GPUs including TDX B300, H200, H100",
        who_measures="Physical hardware verification",
        how_can_miners_game="Claiming GPUs that aren't actually available, inflating specs",
        what_does_maximizing_produce="More GPU supply — but without customer demand visible",
        does_commodity_have_external_demand="Unknown — no public customer revenue total",
        gaming_risks=[
            "Hardware inventory inflation",
            "Claiming TDX capability without actual TEE hardware",
        ],
        concentration_risks=[
            "400 TAO/day emissions ≈ $30M/yr at current prices",
            "No visible customer revenue to justify emissions",
        ],
        alignment_notes="Fascinating infra, unproven demand — excellent technology but missing demand-side evidence",
        evidence=[
            "248+ listed GPUs with TDX capability",
            "Co-authored whitepaper with Intel",
            "Confidential H200s at $3.29/GPU-hour",
        ],
        open_questions=[
            "What is actual customer rental revenue?",
            "What is GPU utilization rate?",
            "How many unique customers?",
        ],
    ),
}


def get_autopsy(netuid: int) -> IncentiveMechanism | None:
    return AUTOPSY_REGISTRY.get(netuid)


def list_autopsies() -> list[IncentiveMechanism]:
    return list(AUTOPSY_REGISTRY.values())


def autopsy_to_markdown(mechanism: IncentiveMechanism) -> str:
    """Convert an autopsy to markdown."""
    lines = []
    lines.append(f"## {mechanism.netuid}. {mechanism.name} — Incentive Mechanism Autopsy\n")

    lines.append("### Core Questions\n")
    lines.append(f"**What is measured?** {mechanism.what_is_measured}")
    lines.append(f"**Who measures?** {mechanism.who_measures}")
    lines.append(f"**How can miners game it?** {mechanism.how_can_miners_game}")
    lines.append(f"**What does maximizing rewards produce?** {mechanism.what_does_maximizing_produce}")
    lines.append(f"**Does the commodity have external demand?** {mechanism.does_commodity_has_external_demand}")
    lines.append("")

    if mechanism.gaming_risks:
        lines.append("### Gaming Risks\n")
        for risk in mechanism.gaming_risks:
            lines.append(f"- {risk}")
        lines.append("")

    if mechanism.concentration_risks:
        lines.append("### Concentration Risks\n")
        for risk in mechanism.concentration_risks:
            lines.append(f"- {risk}")
        lines.append("")

    lines.append(f"### Alignment Assessment\n{mechanism.alignment_notes}\n")

    if mechanism.evidence:
        lines.append("### Evidence\n")
        for e in mechanism.evidence:
            lines.append(f"- {e}")
        lines.append("")

    if mechanism.open_questions:
        lines.append("### Open Questions\n")
        for q in mechanism.open_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)
