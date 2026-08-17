"""The CLI's suggested commands must be copy-pasteable for every entry path.

init's "Ready. Try:" hints once hardcoded the installed script name, which is only on PATH
for the installed script — a zipapp or `python -m` user was told, by the tool
itself, to run a command that did not exist. _prog() is the fix; these tests pin
the shape it produces for each way the process can be started.
"""

import sys

from collective.cli import _prog


def _invoked_as(monkeypatch, argv0, pythonpath=None):
    monkeypatch.setattr(sys, "argv", [argv0])
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    if pythonpath is None:
        monkeypatch.delenv("PYTHONPATH", raising=False)
    else:
        monkeypatch.setenv("PYTHONPATH", pythonpath)


def test_installed_script(monkeypatch):
    _invoked_as(monkeypatch, "/usr/local/bin/collective")
    assert _prog() == "collective"


def test_zipapp(monkeypatch):
    _invoked_as(monkeypatch, "dist/collective.pyz")
    assert _prog() == "python3 dist/collective.pyz"


def test_python_dash_m_from_checkout_carries_pythonpath(monkeypatch):
    _invoked_as(monkeypatch, "/repo/src/collective/__main__.py", pythonpath="src")
    assert _prog() == "PYTHONPATH=src python3 -m collective"


def test_python_dash_m_installed(monkeypatch):
    _invoked_as(monkeypatch, "/site-packages/collective/cli.py")
    assert _prog() == "python3 -m collective"


def test_unknown_entry_falls_back_to_script_name(monkeypatch):
    _invoked_as(monkeypatch, "")
    assert _prog() == "collective"
