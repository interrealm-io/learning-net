#!/usr/bin/env python3
"""One command from a clean clone to the running web explorer.

    python3 demo.py        # macOS / Linux
    py demo.py             # Windows

Creates a private .venv, installs collective into it, downloads and builds the
mirror (first run only, ~900MB), then serves the explorer in a browser tab.
Every step is skipped once its work exists, so this is also the fastest way to
relaunch later. Extra arguments go to `collective web`:

    python3 demo.py --port 9000

A plain .sh/.ps1 pair would need two scripts kept in sync; Python is the one
thing every user of this project already has, on every OS, so the launcher is
Python too. Stdlib only, same rule as the package itself.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts" if os.name == "nt" else "bin") / (
    "python.exe" if os.name == "nt" else "python"
)


def run(*cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        return 0

    if sys.version_info < (3, 11):  # noqa: UP036 — the guard exists FOR old interpreters
        sys.exit(f"collective needs Python 3.11+; this is {sys.version.split()[0]}")

    if not PY.exists():
        print("  creating .venv (first run only) ...")
        import venv

        try:
            venv.EnvBuilder(with_pip=True).create(VENV)
        except Exception:
            # Debian/Ubuntu ship python3 without ensurepip: the venv module
            # imports fine but pip bootstrap fails until python3-venv exists.
            print(
                "  could not create a venv. On Debian/Ubuntu run:  "
                "sudo apt install python3-venv",
                file=sys.stderr,
            )
            raise

    probe = subprocess.run([str(PY), "-c", "import collective"], capture_output=True, check=False)
    if probe.returncode:
        print("  installing collective into .venv ...")
        run(str(PY), "-m", "pip", "install", "--quiet", "--editable", ".")

    # Same default path the CLI uses; a mirror there means init already ran.
    if not (ROOT / "data" / "kg.sqlite").exists():
        run(str(PY), "-m", "collective", "init")

    run(str(PY), "-m", "collective", "web", "--open", *sys.argv[1:])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)  # Ctrl-C is how you stop the server; not an error
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)  # the failing step already printed its own error
