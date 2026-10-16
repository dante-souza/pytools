"""Application-independent integration example: no tool-calling or agent SDK."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from logger_general import GeneralLogger, JsonlWriter, render_json, view_file

OUTPUT = Path(__file__).resolve().parent / "output"
CUSTOM_RULES = {"deployment": {"deployed": "success", "rollback": "error"}}


def run(*, color: str = "always", generate_only: bool = False) -> None:
    OUTPUT.mkdir(exist_ok=True)
    events = [
        {"event_id": "e1", "deployment": "deployed", "attempts": 1,
         "active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"event_id": "e2", "deployment": "rollback", "attempts": 2,
         "active": False, "description": "Teste com acentuação e emoji 🧪"},
    ]
    path = OUTPUT / "application.jsonl"
    if path.exists():
        path.unlink()  # regenerate demonstration fixture; never used on actual app data
    with GeneralLogger(name="example.app", color=color,
                       console=not generate_only, log_file=OUTPUT / "application.log") as logger:
        logger.info("Starting demonstration application")
        with JsonlWriter(path) as writer:
            for event in events:
                writer.write(event)
                logger.info(f"Generated metadata for {event['event_id']}")
    print(f"[EXAMPLE] Generated {path.relative_to(OUTPUT.parent.parent)}")
    if not generate_only:
        print("\n--- Custom semantic field: deployment ---")
        print(render_json(events, color=color, semantic_rules=CUSTOM_RULES))
        print("\n--- Stored JSONL, read-only view ---")
        view_file(path, color=color, pretty=True, semantic_rules=CUSTOM_RULES)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--generate-only", action="store_true")
    p.add_argument("--color", choices=("auto", "always", "never"), default="always")
    args = p.parse_args()
    run(color=args.color, generate_only=args.generate_only)
