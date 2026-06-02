from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
VENV_DIR = APP_ROOT / ".venv"
R_LIBRARY_DIR = APP_ROOT / ".r-library"
LOG_DIR = APP_ROOT / "install_logs"
RUN_APP = APP_ROOT / "run_app.py"
PYTHON_MINIMUM = (3, 10)


class InstallerError(RuntimeError):
    pass


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def write_line(message: str, log_file: Path | None = None) -> None:
    print(message, flush=True)
    if log_file is not None:
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


def run_command(
    command: list[str],
    log_file: Path,
    *,
    cwd: Path = APP_ROOT,
    env: dict[str, str] | None = None,
) -> None:
    write_line(f"$ {' '.join(command)}", log_file)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        write_line(line.rstrip(), log_file)
    code = proc.wait()
    if code != 0:
        raise InstallerError(f"Command failed with exit code {code}: {' '.join(command)}")


def ensure_supported_python() -> None:
    if sys.version_info < PYTHON_MINIMUM:
        required = ".".join(map(str, PYTHON_MINIMUM))
        found = platform.python_version()
        raise InstallerError(f"Python {required}+ is required. Found Python {found}.")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def create_virtualenv(log_file: Path) -> Path:
    python_exe = venv_python()
    if not python_exe.exists():
        write_line("Creating Python virtual environment in .venv ...", log_file)
        run_command([sys.executable, "-m", "venv", str(VENV_DIR)], log_file)
    else:
        write_line("Using existing Python virtual environment in .venv.", log_file)
    return python_exe


def install_python_package(python_exe: Path, log_file: Path) -> None:
    run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], log_file)
    run_command([str(python_exe), "-m", "pip", "install", "-e", str(APP_ROOT)], log_file)


def find_rscript() -> str:
    found = shutil.which("Rscript")
    if found:
        return found

    candidates: list[Path] = []
    if os.name == "nt":
        candidates.extend([
            Path("C:/Program Files/R/R-4.5.0/bin/Rscript.exe"),
            Path("C:/Program Files/R/R-4.4.0/bin/Rscript.exe"),
            Path("C:/Program Files/R"),
        ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Library/Frameworks/R.framework/Resources/bin/Rscript"),
            Path("/opt/homebrew/bin/Rscript"),
            Path("/usr/local/bin/Rscript"),
        ])
    else:
        candidates.extend([
            Path("/usr/bin/Rscript"),
            Path("/usr/local/bin/Rscript"),
        ])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
        if candidate.is_dir():
            hits = sorted(candidate.glob("R-*/bin/Rscript.exe"), reverse=True)
            if hits:
                return str(hits[0])

    raise InstallerError(
        "Rscript was not found. Install R first, then rerun this installer. "
        "Windows: install R from CRAN. macOS: install R from CRAN or Homebrew. "
        "Linux: install r-base with your package manager."
    )


def install_r_packages(rscript: str, log_file: Path) -> None:
    R_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    env = {"OSCC_R_LIBRARY": str(R_LIBRARY_DIR)}
    run_command(
        [
            rscript,
            str(APP_ROOT / "backend_r" / "install_r_packages.R"),
            str(R_LIBRARY_DIR),
        ],
        log_file,
        env=env,
    )


def launcher_target() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(APP_ROOT))) / "Microsoft" / "WindowsApps"
        return base / "oscc.cmd"
    return Path.home() / ".local" / "bin" / "oscc"


def create_launcher(python_exe: Path, log_file: Path) -> Path:
    target = launcher_target()
    target.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        content = f'@echo off\n"{python_exe}" "{RUN_APP}" %*\n'
    else:
        content = f'#!/usr/bin/env sh\n"{python_exe}" "{RUN_APP}" "$@"\n'

    target.write_text(content, encoding="utf-8")
    if os.name != "nt":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    write_line(f"Created launcher: {target}", log_file)
    return target


def path_contains(path: Path) -> bool:
    needle = str(path.resolve())
    for value in os.environ.get("PATH", "").split(os.pathsep):
        if not value:
            continue
        try:
            if str(Path(value).resolve()) == needle:
                return True
        except OSError:
            continue
    return False


def run_smoke_tests(python_exe: Path, log_file: Path, *, include_r: bool) -> None:
    run_command([str(python_exe), str(APP_ROOT / "scripts" / "smoke_test.py")], log_file)
    if include_r:
        run_command([str(python_exe), str(APP_ROOT / "scripts" / "smoke_test_r_preprocess.py")], log_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install OSCC Survival Risk Predictor.")
    parser.add_argument("--skip-r", action="store_true", help="Skip R package installation.")
    parser.add_argument("--skip-smoke-tests", action="store_true", help="Skip post-install smoke tests.")
    parser.add_argument("--skip-r-smoke-test", action="store_true", help="Skip the full R preprocessing smoke test.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"install-{timestamp()}.log"

    try:
        write_line("Installing OSCC Survival Risk Predictor", log_file)
        write_line(f"Application folder: {APP_ROOT}", log_file)
        write_line(f"Operating system: {platform.platform()}", log_file)
        write_line(f"Python: {platform.python_version()} ({sys.executable})", log_file)

        ensure_supported_python()
        python_exe = create_virtualenv(log_file)
        install_python_package(python_exe, log_file)

        if args.skip_r:
            write_line("Skipping R package installation.", log_file)
        else:
            rscript = find_rscript()
            write_line(f"Rscript: {rscript}", log_file)
            install_r_packages(rscript, log_file)

        launcher = create_launcher(python_exe, log_file)

        if args.skip_smoke_tests:
            write_line("Skipping smoke tests.", log_file)
        else:
            run_smoke_tests(python_exe, log_file, include_r=not args.skip_r and not args.skip_r_smoke_test)

        write_line("", log_file)
        write_line("Installation complete.", log_file)
        write_line("Run the app with: oscc", log_file)
        if not path_contains(launcher.parent):
            write_line(f"Note: {launcher.parent} is not currently on PATH.", log_file)
            write_line(f"You can still run the launcher directly: {launcher}", log_file)
        write_line(f"Install log: {log_file}", log_file)
        return 0
    except Exception as exc:
        write_line("", log_file)
        write_line(f"Installation failed: {exc}", log_file)
        write_line(f"Install log: {log_file}", log_file)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
