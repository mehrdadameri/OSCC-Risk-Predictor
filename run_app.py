from __future__ import annotations

from src.cli import run_app


def main() -> int:
    return run_app(port=8502)


if __name__ == "__main__":
    raise SystemExit(main())
