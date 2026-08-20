"""collective — command line interface.

    collective init    [--version V]                 download + build, one command
    collective build   <export-dir>                  build a mirror from a local export
    collective sync    [--version V] [--check]       fetch, diff, report, rebuild
    collective update                                is there a newer upstream release?
    collective coverage [--csv f]                    alignment gap map by jurisdiction
    collective status                                what is in the mirror, how stale
    collective serve                                 MCP server on stdio
    collective web                                   web explorer UI
    collective query   <tool> [k=v ...]              one-shot query, JSON out

Every command takes --db PATH, on either side of the subcommand.
The mirror path defaults to $COLLECTIVE_DB, then ./data/kg.sqlite.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

DEFAULT_DB = os.environ.get("COLLECTIVE_DB") or os.path.join("data", "kg.sqlite")
DEFAULT_EXPORT_DIR = "data/export"


def _db(args):
    return os.path.expanduser(getattr(args, "db", None) or DEFAULT_DB)


def _prog():
    """The invocation to print in hints, exactly as the user would retype it.

    Every suggested command (init's "Ready. Try:", sync's rebuild line, ...) must
    be copy-pasteable for however this process was started. `collective` is only
    on PATH for the installed script — a zipapp or `python -m` user who pastes it
    gets "command not found" from the tool's own advice.
    """
    import zipfile

    argv0 = sys.argv[0] or ""
    base = os.path.basename(argv0)
    if base in ("collective", "collective.exe"):
        return "collective"
    py = os.path.basename(sys.executable or "") or "python3"
    if argv0.endswith(".pyz") or zipfile.is_zipfile(argv0):
        return f"{py} {argv0}"
    if base in ("cli.py", "__main__.py"):
        # python -m out of a checkout: the import only worked because of
        # PYTHONPATH, so the hint has to carry it too.
        pp = os.environ.get("PYTHONPATH")
        prefix = f"PYTHONPATH={pp} " if pp else ""
        return f"{prefix}{py} -m collective"
    return "collective"


def _fmt_prov(prov):
    print("\n  provenance:")
    for k, v in prov.items():
        print(f"    {k:<22} {v}")


def cmd_init(args):
    """Download a versioned export and build a mirror. The whole setup."""
    from .build import build
    from .sync import DEFAULT_VERSION, export_url, fetch

    version = args.version or DEFAULT_VERSION
    export = os.path.expanduser(args.dir or DEFAULT_EXPORT_DIR)
    db = _db(args)

    print(f"  Collective — initialising from Learning Commons v{version}\n")
    print(f"  source  {export_url('nodes.jsonl', version)}")
    print(f"  export  {export}")
    print(f"  mirror  {db}\n")

    if args.skip_download:
        print("  --skip-download: using files already in the export directory\n")
    else:
        try:
            sizes = fetch(export, version, log=lambda s, end="\n": print(s, end=end, flush=True))
        except RuntimeError as e:
            print(f"\n  download failed: {e}", file=sys.stderr)
            print(
                "\n  You can download by hand and re-run with --skip-download:\n"
                f"    curl -L '{export_url('nodes.jsonl', version)}' -o {export}/nodes.jsonl\n"
                f"    curl -L '{export_url('relationships.jsonl', version)}' "
                f"-o {export}/relationships.jsonl",
                file=sys.stderr,
            )
            return 1
        print(f"\n  downloaded {sum(sizes.values()) / 1e6:.0f} MB\n")

    prov = build(export, db, source=f"learning-commons-cdn-v{version}", kg_version=version)
    _fmt_prov(prov)
    prog = _prog()
    print("\n  Ready. Try:")
    print(f"    {prog} status --db {db}")
    print(f"    {prog} query search query='fractions' --db {db}")
    return 0


def cmd_build(args):
    from .build import build

    prov = build(
        os.path.expanduser(args.export_dir),
        _db(args),
        source=args.source,
        kg_version=args.kg_version,
    )
    _fmt_prov(prov)
    return 0


def cmd_update(args):
    from .sync import DEFAULT_VERSION, discover_versions, mirror_version

    have = mirror_version(_db(args)) or DEFAULT_VERSION
    print(f"  mirror is built from v{have}")
    print("  probing for newer releases (upstream publishes no manifest)...")
    newest = discover_versions(have, log=print)
    if newest == have:
        print("\n  no newer release found.")
        print(
            "  Probing is a guess, not an answer — confirm at\n"
            "  https://docs.learningcommons.org/knowledge-graph/using-knowledge-graph/local-files"
        )
        return 0
    print(f"\n  v{newest} is available.  Update with:  {_prog()} sync --version {newest}")
    return 0


def cmd_sync(args):
    from .sync import (
        DEFAULT_VERSION,
        changelog,
        diff_shapes,
        has_breaking,
        mirror_version,
        render_diff,
        shape_of_export,
        shape_of_mirror,
    )

    db = _db(args)
    if not os.path.exists(db):
        print(f"no mirror at {db} — run `{_prog()} init` first", file=sys.stderr)
        return 2

    version = args.version or DEFAULT_VERSION
    export = os.path.expanduser(args.dir or DEFAULT_EXPORT_DIR)

    if args.export_dir:
        export = os.path.expanduser(args.export_dir)
    elif not args.skip_download:
        from .sync import fetch

        print(f"  fetching v{version}\n")
        try:
            fetch(export, version, log=lambda s, end="\n": print(s, end=end, flush=True))
        except RuntimeError as e:
            print(f"  download failed: {e}", file=sys.stderr)
            return 1
        print()

    have = mirror_version(db) or "unknown"
    print(f"  comparing v{version} export at {export}\n         to mirror built from v{have}\n")

    findings = diff_shapes(shape_of_mirror(db), shape_of_export(export))
    print(render_diff(findings))

    if args.changelog:
        path = os.path.expanduser(args.changelog)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(changelog(findings, have, version), fh, indent=1)
        print(f"\n  changelog written to {path}")

    if has_breaking(findings):
        print(
            "\n  BREAKING structural change upstream. Review before rebuilding — a "
            "consumer written against the current mirror may now return wrong or "
            "empty results.\n  Rebuild anyway with:  "
            f"{_prog()} build {export} --db {db} --kg-version {version}"
        )
        return 1
    if args.check:
        return 0
    if findings or have != version:
        print("\n  no breaking change; rebuilding.")
        from .build import build

        build(export, db, source=f"learning-commons-cdn-v{version}", kg_version=version)
    return 0


def cmd_coverage(args):
    """The alignment-coverage report — the gap map nobody publishes."""
    import csv

    from .graph import Graph, GraphError

    try:
        g = Graph(_db(args))
    except GraphError as e:
        print(e, file=sys.stderr)
        return 2
    rep = g.coverage_report(args.subject)
    nat, rows = rep["national"], rep["byJurisdiction"]
    snap = rep.get("generatedFrom") or {}

    print(f"  Learning Commons KG v{snap.get('kgVersion', '?')} — alignment coverage")
    if args.subject:
        print(f"  subject: {args.subject}")
    print()
    print(f"  {nat['standards']:,} standards across {nat['jurisdictions']} jurisdictions")
    print(f"  {nat['crosswalked']:,} carry a cross-jurisdiction alignment "
          f"({nat['crosswalkPct']}%)")
    print(f"  {nat['jurisdictionsWithNoCrosswalk']} jurisdictions have NONE — "
          f"{nat['standardsInIsolatedJurisdictions']:,} standards unverifiable\n")

    print(f"  {'jurisdiction':<22}{'standards':>10}{'crosswalk':>11}{'components':>12}"
          f"{'curriculum':>12}{'progression':>13}")
    print("  " + "-" * 78)
    for r in rows:
        mark = "  !" if r["isolated"] else "   "
        print(f"  {r['jurisdiction']:<22}{r['standards']:>10,}"
              f"{r['crosswalkPct']:>10.1f}%{r['componentsPct']:>11.1f}%"
              f"{r['withCurriculum']:>12,}{r['withProgression']:>13,}{mark}")
    print("\n  ! = no alignment edges at all; claims cannot be verified in either direction")

    if args.json:
        with open(os.path.expanduser(args.json), "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)
        print(f"\n  json written to {args.json}")
    if args.csv:
        with open(os.path.expanduser(args.csv), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"  csv written to {args.csv}")
    g.close()
    return 0


def cmd_status(args):
    from .graph import Graph, GraphError

    try:
        g = Graph(_db(args))
    except GraphError as e:
        print(e, file=sys.stderr)
        return 2
    s = g.stats()
    snap = s.get("snapshot") or {}
    print(f"  mirror   {_db(args)}")
    if snap:
        print(f"  upstream Learning Commons KG v{snap.get('kgVersion', 'unknown')}")
        print(f"  built    {snap.get('builtAt', '?')}   source: {snap.get('source', '?')}")
    print(f"  nodes    {sum(s['nodesByLabel'].values()):,}")
    print(f"  edges    {sum(s['edgesByLabel'].values()):,}")
    print(f"\n  {len(s['jurisdictions'])} jurisdictions, {len(s['subjects'])} subjects\n")
    for label, n in s["nodesByLabel"].items():
        print(f"    {n:>9,}  {label}")
    print()
    for label, n in s["edgesByLabel"].items():
        print(f"    {n:>9,}  {label}")
    g.close()
    return 0


def cmd_serve(args):
    from .server import serve

    serve(_db(args))
    return 0


def cmd_web(args):
    from .graph import GraphError
    from .web import web

    try:
        web(_db(args), host=args.host, port=args.port, open_browser=args.open)
    except GraphError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


def cmd_query(args):
    from .graph import Graph, GraphError

    g = Graph(_db(args))
    kw = {}
    for pair in args.params:
        if "=" not in pair:
            print(f"bad param {pair!r}, expected key=value", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        # The MCP tool schemas use camelCase (JSON convention) and the Python
        # methods use snake_case. Someone reading a param name off the tool
        # schema and typing it here should not have to know that.
        k = re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower()
        kw[k] = int(v) if v.isdigit() else v
    fn = {
        "stats": g.stats,
        "find": g.find_standard,
        "search": g.search_standards,
        "list": g.list_standards,
        "components": g.learning_components,
        "search_components": g.search_learning_components,
        "progression": g.progression,
        "crosswalk": g.crosswalk,
        "verify": g.verify_alignment_claim,
        "coverage": g.coverage_report,
        "context": g.context,
        "curriculum": g.curriculum,
        "node": g.node,
    }.get(args.tool)
    if not fn:
        print(f"unknown tool {args.tool!r}", file=sys.stderr)
        return 2
    try:
        print(json.dumps(fn(**kw), indent=1))
    except (GraphError, TypeError) as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    # --db is accepted on either side of the subcommand. Both read naturally
    # (`collective --db X status` and `collective status --db X`) and people
    # write both, so neither should be an error. SUPPRESS keeps the later parse
    # from overwriting a value supplied earlier; _db() reads it with getattr.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--db", default=argparse.SUPPRESS, help=f"mirror path (default {DEFAULT_DB})"
    )

    p = argparse.ArgumentParser(
        prog=_prog(), description=__doc__.split("\n")[0], parents=[common]
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", parents=[common], help="download an export and build a mirror")
    i.add_argument("--version", help="Learning Commons KG version, e.g. 1.12.0")
    i.add_argument("--dir", help=f"where to put the export (default {DEFAULT_EXPORT_DIR})")
    i.add_argument("--skip-download", action="store_true", help="use files already present")
    i.set_defaults(fn=cmd_init)

    b = sub.add_parser("build", parents=[common], help="build a mirror from a local export")
    b.add_argument("export_dir")
    b.add_argument("--source", default="local-export")
    b.add_argument("--kg-version", help="upstream release this export came from")
    b.set_defaults(fn=cmd_build)

    s = sub.add_parser("sync", parents=[common], help="fetch, diff against the mirror, rebuild")
    s.add_argument("export_dir", nargs="?", help="use a local export instead of downloading")
    s.add_argument("--version", help="upstream version to fetch")
    s.add_argument("--dir", help="where to put the fetched export")
    s.add_argument("--check", action="store_true", help="report only, never rebuild")
    s.add_argument("--skip-download", action="store_true")
    s.add_argument("--changelog", help="write the structural changelog to this JSON path")
    s.set_defaults(fn=cmd_sync)

    u = sub.add_parser("update", parents=[common], help="probe for a newer upstream release")
    u.set_defaults(fn=cmd_update)

    cv = sub.add_parser(
        "coverage", parents=[common], help="alignment-coverage report by jurisdiction"
    )
    cv.add_argument("--subject", help="restrict to one subject")
    cv.add_argument("--json", help="also write the full report to this JSON path")
    cv.add_argument("--csv", help="also write the per-jurisdiction table to this CSV path")
    cv.set_defaults(fn=cmd_coverage)


    st = sub.add_parser(
        "status", parents=[common], help="what is in the mirror and how stale it is"
    )
    st.set_defaults(fn=cmd_status)

    sv = sub.add_parser("serve", parents=[common], help="run the MCP server on stdio")
    sv.set_defaults(fn=cmd_serve)

    w = sub.add_parser("web", parents=[common], help="web explorer UI over the mirror")
    w.add_argument("--host", default="127.0.0.1", help="bind address (default localhost only)")
    w.add_argument("--port", type=int, default=8788)
    w.add_argument("--open", action="store_true", help="open a browser tab")
    w.set_defaults(fn=cmd_web)

    q = sub.add_parser("query", parents=[common], help="one-shot query against the mirror")
    q.add_argument("tool")
    q.add_argument("params", nargs="*")
    q.set_defaults(fn=cmd_query)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
