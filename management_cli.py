"""Command-line entry point for the read-only management agent."""
from __future__ import annotations

import argparse
import json

from management_agent import ManagementAgent, ManagementConfig, ManagementDataProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Company AI management agent")
    parser.add_argument("--days", type=int, default=30, help="Analysis window in days")
    parser.add_argument("--provider", choices=["mysql", "sqlite"], help="Data provider override")
    parser.add_argument("--question", help="Ask one management question")
    parser.add_argument("--no-llm", action="store_true", help="Use deterministic grounded answers only")
    parser.add_argument("--json", action="store_true", help="Print the analysis report as JSON")
    args = parser.parse_args()

    provider = ManagementDataProvider(ManagementConfig(provider=args.provider)) if args.provider else None
    agent = ManagementAgent(provider)
    if args.json:
        print(json.dumps(agent.analyze(args.days), ensure_ascii=False, default=str, indent=2))
    elif args.question:
        print(agent.answer(args.question, days=args.days, use_llm=not args.no_llm))
    else:
        report = agent.analyze(args.days)
        print("Management analysis")
        print(json.dumps(report["recommendations"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
