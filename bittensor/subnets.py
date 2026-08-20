"""Bittensor subnet registry — what each subnet does, who runs it, what it incentivizes."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Subnet:
    """A Bittensor subnet."""
    netuid: int
    name: str
    ticker: str | None = None
    description: str = ""
    commodity: str = ""  # what miners produce
    validator_method: str = ""  # how quality is measured
    anti_cheat: str = ""  # gaming resistance mechanism
    external_revenue_known: bool = False
    external_revenue_usd: float | None = None
    github_repo: str | None = None
    website: str | None = None
    thesis_category: str = ""  # maps to our thesis categories

# Manually curated from research — extend as we discover more
SUBNET_REGISTRY: dict[int, Subnet] = {
    4: Subnet(
        netuid=4,
        name="Targon",
        ticker="TARGON",
        description="Confidential compute via Intel TDX + NVIDIA GPUs. Manifold team (Austin, backed by OSS Capital, DCG).",
        commodity="GPU compute (confidential inference)",
        validator_method="Miner payouts, GPU inventory verification",
        anti_cheat="Physical hardware verification",
        external_revenue_known=False,
        github_repo="manifoldlabs/targon",
        website="https://targon.com",
        thesis_category="verifiable_execution",
    ),
    28: Subnet(
        netuid=28,
        name="gm",
        description="Inference router for Claude + GPT + Gemini. Uses Phala Cloud CVMs.",
        commodity="API routing/discounts for frontier models",
        validator_method="API response verification",
        anti_cheat="Credential routing through TEE",
        external_revenue_known=False,
        website="https://gm.ai",
        thesis_category="agent_economy",
    ),
    51: Subnet(
        netuid=51,
        name="Lium",
        commodity="GPU rental marketplace",
        validator_method="Provider pricing, rental fulfillment",
        anti_cheat="Platform 5% take rate verification",
        external_revenue_known=False,
        website="https://lium.io",
        thesis_category="decentralized_compute",
    ),
    53: Subnet(
        netuid=53,
        name="engy",
        commodity="Verified inference (TOPLOC activation fingerprints)",
        validator_method="Model weight commitments + activation fingerprints + sampled recomputation",
        anti_cheat="Cryptographic commitments + auditing",
        external_revenue_known=False,
        github_repo="hanlinai/engy",
        thesis_category="proof_generation",
    ),
    64: Subnet(
        netuid=64,
        name="Chutes",
        ticker="CHUTES",
        description="Decentralized serverless AI inference. TEE infrastructure. ~$5.33M annualized revenue.",
        commodity="Serverless AI inference (PAYG + subscriptions)",
        validator_method="Revenue verification, TEE attestation",
        anti_cheat="TEE infrastructure + abuse removal",
        external_revenue_known=True,
        external_revenue_usd=5_330_000,
        github_repo="chutes-ai",
        website="https://chutes.ai",
        thesis_category="verifiable_execution",
    ),
    80: Subnet(
        netuid=80,
        name="OpenRoboto",
        commodity="Robot learning models (VLA training)",
        validator_method="Simulated robotics task execution",
        anti_cheat="Benchmark contamination controls",
        external_revenue_known=False,
        github_repo="openroboto-ai/openroboto-subnet",
        thesis_category="physical_ai",
    ),
    90: Subnet(
        netuid=90,
        name="KubeTEE",
        commodity="Confidential compute (TEE)",
        validator_method="TEE attestation verification",
        anti_cheat="Hardware-based attestation",
        external_revenue_known=False,
        thesis_category="verifiable_execution",
    ),
    108: Subnet(
        netuid=108,
        name="Agent Launchpad",
        commodity="Agent-to-agent services",
        validator_method="Agent service quality",
        anti_cheat="Economic independence verification",
        external_revenue_known=False,
        github_repo="subnet108/internet-of-intelligence",
        thesis_category="agent_economy",
    ),
    118: Subnet(
        netuid=118,
        name="Ditto",
        commodity="Agent memory harnesses",
        validator_method="DittoBench: tool calling + memory recall",
        anti_cheat="Sandboxed validator execution",
        external_revenue_known=False,
        github_repo="ditto-assistant/ditto-subnet",
        thesis_category="agent_economy",
    ),
}

def get_subnet(netuid: int) -> Subnet | None:
    return SUBNET_REGISTRY.get(netuid)

def list_subnets() -> list[Subnet]:
    return list(SUBNET_REGISTRY.values())

def subnets_by_category(category: str) -> list[Subnet]:
    return [s for s in SUBNET_REGISTRY.values() if s.thesis_category == category]
