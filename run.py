"""Run the full crypto-lab pipeline."""
from __future__ import annotations
import asyncio
import sys
from ingestion import get_db, init_schema

async def main():
    conn = get_db()
    init_schema(conn)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
    else:
        cmd = "full"

    if cmd == "scout":
        from agent.scout import scout_cycle
        result = await scout_cycle(conn)
        print(f"Scout: {result}")

    elif cmd == "monitor":
        from agent.scout import monitor_cycle
        result = await monitor_cycle(conn)
        print(f"Monitor: {result}")

    elif cmd == "report":
        from agent.analyst import generate_report
        report = generate_report(conn)
        print(report)

    elif cmd == "score":
        from agent.scoring import score_all
        from ingestion.entities import ENTITY_MAP
        for pid in ENTITY_MAP:
            r = score_all(conn, pid)
            print(f"{pid}: {r['total_score']:.1f}")

    elif cmd == "full":
        # Full pipeline
        print("=== CRYPTO LAB ===\n")

        print("1. Scout cycle (ingest + discover)...")
        from agent.scout import scout_cycle
        scout_result = await scout_cycle(conn)
        print(f"   Done: {scout_result}\n")

        print("2. Score all projects...")
        from agent.scoring import score_all
        from ingestion.entities import ENTITY_MAP
        for pid in ENTITY_MAP:
            r = score_all(conn, pid)
            print(f"   {pid}: {r['total_score']:.1f}")
        print()

        print("3. Generate report...")
        from agent.analyst import generate_report
        report = generate_report(conn)
        from pathlib import Path
        report_path = Path(__file__).parent.parent / "data" / "report.md"
        report_path.write_text(report)
        print(f"   Saved to {report_path}\n")

        print("=== COMPLETE ===")

    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
