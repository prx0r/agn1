"""Analyst agent — scores projects and generates reports."""
from __future__ import annotations
import json
from typing import Any
from datetime import datetime

def generate_report(conn) -> str:
    """Generate a markdown report of all scored projects."""
    from agent.scoring import score_all
    from ingestion.entities import ENTITY_MAP

    lines = []
    lines.append("# Crypto Lab — Intelligence Report")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Score all projects
    scored = []
    for project_id in ENTITY_MAP:
        result = score_all(conn, project_id)
        scored.append(result)

    # Sort by total score
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    lines.append("## Project Rankings\n")
    lines.append("| Rank | Project | Total | Dev | Thesis | Valuation |")
    lines.append("|------|---------|-------|-----|--------|-----------|")

    for i, s in enumerate(scored, 1):
        lines.append(
            f"| {i} | {s['project_id']} | **{s['total_score']:.1f}** | "
            f"{s['dev_reality']['score']:.1f} | {s['thesis_fit']['score']:.1f} | "
            f"{s['valuation']['score']:.1f} |"
        )

    lines.append("\n## Detailed Scores\n")
    for s in scored:
        if s["total_score"] > 0:
            lines.append(f"### {s['project_id']} ({s['total_score']:.1f}/40)")
            lines.append(f"- **Dev Reality:** {s['dev_reality']['score']:.1f}/20 — {s['dev_reality']['status']}")
            lines.append(f"- **Thesis Fit:** {s['thesis_fit']['score']:.1f}/25 — {s['thesis_fit']['status']}")
            lines.append(f"- **Valuation:** {s['valuation']['score']:.1f}/10 — {s['valuation']['status']}")
            lines.append("")

    # Recent discoveries
    lines.append("## Recent Discoveries\n")
    obs_rows = conn.execute("""
        SELECT project_id, data, observed_at FROM observations
        WHERE source = 'discovery'
        ORDER BY observed_at DESC LIMIT 20
    """).fetchall()

    for row in obs_rows:
        data = json.loads(row[1]) if row[1] else {}
        lines.append(f"- **{data.get('repo', row[0])}** — {data.get('description', '')[:80]}")

    return "\n".join(lines)

def answer_question(conn, question: str) -> str:
    """Answer a question about the portfolio using stored data."""
    q = question.lower()

    if "best" in q or "top" in q or "highest" in q:
        rows = conn.execute("""
            SELECT project_id, score FROM scores
            WHERE score_type = 'dev_reality'
            ORDER BY score DESC LIMIT 5
        """).fetchall()
        return "Top projects by dev reality:\n" + "\n".join(
            f"- {row[0]}: {row[1]}" for row in rows
        )

    if "worst" in q or "lowest" in q:
        rows = conn.execute("""
            SELECT project_id, score FROM scores
            WHERE score_type = 'dev_reality'
            ORDER BY score ASC LIMIT 5
        """).fetchall()
        return "Lowest projects by dev reality:\n" + "\n".join(
            f"- {row[0]}: {row[1]}" for row in rows
        )

    if "thesis" in q:
        rows = conn.execute("""
            SELECT project_id, score FROM scores
            WHERE score_type = 'thesis_fit'
            ORDER BY score DESC LIMIT 5
        """).fetchall()
        return "Best thesis fit:\n" + "\n".join(
            f"- {row[0]}: {row[1]}" for row in rows
        )

    if "discovery" in q or "new" in q:
        rows = conn.execute("""
            SELECT project_id, data FROM observations
            WHERE source = 'discovery'
            ORDER BY observed_at DESC LIMIT 10
        """).fetchall()
        return "Recent discoveries:\n" + "\n".join(
            f"- {json.loads(row[1]).get('repo', row[0])}" for row in rows
        )

    return "Available questions: 'best projects', 'worst projects', 'thesis fit', 'recent discoveries'"

if __name__ == "__main__":
    from ingestion import get_db, init_schema

    conn = get_db()
    init_schema(conn)

    report = generate_report(conn)
    print(report)

    # Save report
    from pathlib import Path
    report_path = Path(__file__).parent.parent / "data" / "report.md"
    report_path.write_text(report)
    print(f"\n[analyst] Report saved to {report_path}")

    conn.close()
