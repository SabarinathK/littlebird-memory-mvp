import argparse
import sys
import textwrap
from dataclasses import dataclass
from typing import Optional, Sequence

from .agent import CaptureAgent
from .config import CONFIG
from .ui import run_console, run_tray


@dataclass(frozen=True)
class AppOptions:
    mode: str = "console"
    seed_demo: bool = True
    show_banner: bool = True


class LittlebirdApplication:
    def __init__(self, options: Optional[AppOptions] = None):
        self.options = options or AppOptions()
        self.agent: Optional[CaptureAgent] = None

    def run(self) -> int:
        if self.options.show_banner:
            self.print_banner()
        self.validate_config()

        self.agent = self.create_agent()
        self.agent.start()

        if self.options.seed_demo:
            self.seed_test_event(self.agent)

        self.run_interface(self.agent)
        return 0

    def create_agent(self) -> CaptureAgent:
        return CaptureAgent()

    def run_interface(self, agent: CaptureAgent) -> None:
        if self.options.mode == "tray":
            run_tray(agent)
            return
        run_console(agent)

    @staticmethod
    def print_banner() -> None:
        print(
            textwrap.dedent(
                """
            Littlebird Windows Agent v0.1
            Personal AI Memory - MVP
            """
            ).strip()
        )
        print()

    @staticmethod
    def validate_config() -> None:
        if not CONFIG.get("groq_api_key") or CONFIG["groq_api_key"] == "YOUR_GROQ_API_KEY":
            print(
                "ERROR: Set your Groq API key in the environment before starting Littlebird."
            )
            print("Get a free key at: https://console.groq.com")
            raise SystemExit(1)

    @staticmethod
    def seed_test_event(agent: CaptureAgent) -> None:
        agent.pipeline.ingest(
            {
                "id": "test123",
                "type": "screen",
                "source_app": "test",
                "window_title": "test",
                "content": "AI project planning with embeddings and vector database",
                "timestamp": "2026-01-01T00:00:00",
            }
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Littlebird personal memory agent")
    parser.add_argument(
        "--mode",
        choices=("console", "tray"),
        default="console",
        help="Choose how to interact with the running agent.",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip the built-in demo seed event at startup.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide the startup banner.",
    )
    return parser


def parse_options(argv: Optional[Sequence[str]] = None) -> AppOptions:
    args = build_parser().parse_args(argv)
    return AppOptions(
        mode=args.mode,
        seed_demo=not args.no_seed,
        show_banner=not args.quiet,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    app = LittlebirdApplication(parse_options(argv))
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
