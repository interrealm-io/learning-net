"""Sync a Learning Net mirror against upstream Learning Commons.

Three halves, deliberately separable:

  fetch     download a versioned export from the Learning Commons CDN
  discover  find out whether a newer release exists
  diff      compare an export against the live mirror and REPORT what changed

Upstream publishes exports on a public CDN at a version-pinned path:

    https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/nodes.jsonl
    https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/relationships.jsonl

Two consequences worth stating plainly, because both shape this module:

1. No credential is involved, so fetching needs nothing but `urllib` and the
   whole project stays dependency-free. The CC BY-4.0 license already grants
   redistribution; the CDN imposes no additional gate.

2. The version is IN THE PATH, which gives a mirror a real upstream release
   identifier rather than only its own build timestamp. That is the missing
   piece for any downstream that needs to say which release it is a copy of.

What upstream does NOT publish is a `latest` alias, a version manifest, or a
changelog. So `discover` probes, and `diff` reconstructs the changelog. Both are
workarounds for a gap, and both would be better solved upstream — a manifest
endpoint is the single highest-value schema proposal this project could make.
"""

from __future__ import annotations

import collections
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request

CDN_BASE = os.environ.get("LEARNING_COMMONS_CDN", "https://cdn.learningcommons.org")
DEFAULT_VERSION = os.environ.get("LEARNING_COMMONS_KG_VERSION", "1.12.0")
EXPORTS = ("nodes.jsonl", "relationships.jsonl")
USER_AGENT = "learning-net/0.1.0 (+https://github.com/interrealm/learning-net)"


def export_url(name, version=DEFAULT_VERSION, base=CDN_BASE):
    url = f"{base}/knowledge-graph/v{version}/exports/{name}"
    # `ref` is upstream's attribution/analytics parameter — worth sending so
    # Learning Commons can see this traffic is a mirror rather than scraping.
    # Only meaningful over http(s); a file:// base is used by the tests.
    return url + "?ref=learning-net" if base.startswith("http") else url


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------


def _human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def fetch(dest, version=DEFAULT_VERSION, base=CDN_BASE, log=print, chunk=1 << 20):
    """Download the versioned export into `dest`. Returns {name: bytes}.

    The national graph is roughly 900 MB across both files, so this streams to
    disk and reports progress rather than buffering.
    """
    os.makedirs(dest, exist_ok=True)
    written = {}
    for name in EXPORTS:
        url = export_url(name, version, base)
        path = os.path.join(dest, name)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req) as r:  # noqa: S310 - fixed https CDN
                total = int(r.headers.get("Content-Length") or 0)
                done = 0
                with open(path, "wb") as fh:
                    while block := r.read(chunk):
                        fh.write(block)
                        done += len(block)
                        if total:
                            log(
                                f"\r  {name:<22} {_human(done)} / {_human(total)}"
                                f"  ({done * 100 // total}%)",
                                end="",
                            )
                        else:
                            log(f"\r  {name:<22} {_human(done)}", end="")
                log("")
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"{url} returned HTTP {e.code}. "
                f"Version {version} may not exist — check "
                f"https://docs.learningcommons.org/knowledge-graph/using-knowledge-graph/local-files"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"cannot reach {url}: {e.reason}") from e
        written[name] = os.path.getsize(path)
    return written


def _exists(version, base=CDN_BASE, timeout=15):
    """Test whether a release is published, without downloading it.

    HEAD first, then a one-byte ranged GET. Two fallbacks because neither is
    universally safe: CDNs sometimes answer HEAD with 405, and `file://` URLs
    (used by the tests) carry no status code at all. A successful open is the
    real signal — urllib raises HTTPError for 4xx/5xx, so reaching the body
    means the object is there.
    """
    url = export_url("nodes.jsonl", version, base)
    for headers, method in (
        ({"User-Agent": USER_AGENT}, "HEAD"),
        ({"User-Agent": USER_AGENT, "Range": "bytes=0-0"}, "GET"),
    ):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
                status = getattr(r, "status", None)
                return status is None or 200 <= status < 400
        except urllib.error.HTTPError as e:
            if e.code in (403, 405, 501) and method == "HEAD":
                continue  # method not allowed — try the ranged GET
            return False
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False
    return False


def discover_versions(current=DEFAULT_VERSION, base=CDN_BASE, lookahead=3, log=None):
    """Probe for releases newer than `current`.

    Upstream publishes no manifest and no `latest` alias, so there is no way to
    ask. Probing a bounded neighbourhood of the current version is the honest
    fallback: it finds the common cases (patch and minor bumps) and it is
    explicit about being a guess rather than an answer.

    Returns the newest version found, or `current` if nothing newer responds.
    """
    try:
        major, minor, patch = (int(x) for x in current.split("."))
    except ValueError as e:
        raise ValueError(f"version {current!r} is not major.minor.patch") from e

    found = current
    candidates = (
        [f"{major}.{minor}.{patch + i}" for i in range(1, lookahead + 1)]
        + [f"{major}.{minor + i}.0" for i in range(1, lookahead + 1)]
        + [f"{major + 1}.0.0"]
    )
    for v in candidates:
        if _exists(v, base):
            found = v
            if log:
                log(f"  found {v}")
    return found


# ---------------------------------------------------------------------------
# shape
# ---------------------------------------------------------------------------


class Shape:
    """The structural fingerprint of a graph: labels, edge types, property keys.

    Deliberately NOT the data. Two releases will differ in thousands of
    statements and that is uninteresting; what matters is whether the SHAPE
    moved, because that is what breaks a downstream consumer.
    """

    def __init__(self):
        self.node_labels = collections.Counter()
        self.edge_labels = collections.Counter()
        self.triples = collections.Counter()
        self.props = collections.defaultdict(collections.Counter)

    def to_dict(self):
        return {
            "nodeLabels": dict(self.node_labels),
            "edgeLabels": dict(self.edge_labels),
            "triples": {f"{a} -[{b}]-> {c}": v for (a, b, c), v in self.triples.items()},
            "props": {k: dict(v) for k, v in self.props.items()},
        }

    def prop_coverage(self, label, key):
        total = self.node_labels.get(label, 0)
        return (self.props[label].get(key, 0) / total) if total else 0.0


def shape_of_export(export_dir):
    s = Shape()
    with open(os.path.join(export_dir, "nodes.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            lab = (d.get("labels") or [""])[0]
            s.node_labels[lab] += 1
            for k in d.get("properties") or {}:
                s.props[lab][k] += 1
    with open(os.path.join(export_dir, "relationships.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            lab = d.get("label")
            s.edge_labels[lab] += 1
            s.triples[
                (
                    (d.get("source_labels") or [""])[0],
                    lab,
                    (d.get("target_labels") or [""])[0],
                )
            ] += 1
    return s


def shape_of_mirror(db_path):
    s = Shape()
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    for label, n in con.execute("SELECT label, COUNT(*) FROM nodes GROUP BY 1"):
        s.node_labels[label] = n
    for label, n in con.execute("SELECT label, COUNT(*) FROM edges GROUP BY 1"):
        s.edge_labels[label] = n
    for a, b, c, n in con.execute(
        "SELECT src_label, label, dst_label, COUNT(*) FROM edges GROUP BY 1,2,3"
    ):
        s.triples[(a, b, c)] = n
    for label, props in con.execute("SELECT label, props FROM nodes"):
        for k in json.loads(props):
            s.props[label][k] += 1
    con.close()
    return s


def mirror_version(db_path):
    """The upstream release a mirror was built from, if it recorded one."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        row = con.execute("SELECT value FROM meta WHERE key='kgVersion'").fetchone()
        con.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

BREAKING = "breaking"
ADDITIVE = "additive"
INFO = "info"


def diff_shapes(old: Shape, new: Shape, coverage_delta=0.10):
    """Report structural change between two shapes.

    `breaking` means a downstream consumer written against `old` can return
    wrong or empty results against `new`. Those are the findings that should
    stop a sync and be read by a human.
    """
    out = []

    def add(sev, kind, detail):
        out.append({"severity": sev, "kind": kind, "detail": detail})

    for lab in sorted(set(old.node_labels) - set(new.node_labels)):
        add(BREAKING, "node-label-removed", f"{lab} (was {old.node_labels[lab]:,} nodes)")
    for lab in sorted(set(new.node_labels) - set(old.node_labels)):
        add(ADDITIVE, "node-label-added", f"{lab} ({new.node_labels[lab]:,} nodes)")

    for lab in sorted(set(old.edge_labels) - set(new.edge_labels)):
        add(BREAKING, "edge-type-removed", f"{lab} (was {old.edge_labels[lab]:,} edges)")
    for lab in sorted(set(new.edge_labels) - set(old.edge_labels)):
        add(ADDITIVE, "edge-type-added", f"{lab} ({new.edge_labels[lab]:,} edges)")

    for t in sorted(set(old.triples) - set(new.triples)):
        add(BREAKING, "triple-removed", f"{t[0]} -[{t[1]}]-> {t[2]} (was {old.triples[t]:,})")
    for t in sorted(set(new.triples) - set(old.triples)):
        add(ADDITIVE, "triple-added", f"{t[0]} -[{t[1]}]-> {t[2]} ({new.triples[t]:,})")

    for lab in sorted(set(old.node_labels) & set(new.node_labels)):
        for key in sorted(set(old.props[lab]) | set(new.props[lab])):
            o, n = old.prop_coverage(lab, key), new.prop_coverage(lab, key)
            if o > 0 and n == 0:
                add(BREAKING, "property-removed", f"{lab}.{key} (was on {o:.0%} of nodes)")
            elif o == 0 and n > 0:
                add(ADDITIVE, "property-added", f"{lab}.{key} (now on {n:.0%} of nodes)")
            elif abs(n - o) >= coverage_delta:
                sev = BREAKING if n < o else INFO
                add(sev, "property-coverage", f"{lab}.{key}  {o:.0%} → {n:.0%}")

    # Volume swings are not breaking, but a 30% drop in a label is worth a look
    # before anyone points a classroom at the result.
    for lab in sorted(set(old.node_labels) & set(new.node_labels)):
        o, n = old.node_labels[lab], new.node_labels[lab]
        if o and abs(n - o) / o >= 0.30:
            add(INFO, "volume-change", f"{lab}  {o:,} → {n:,}  ({(n - o) / o:+.0%})")

    return out


def render_diff(findings):
    if not findings:
        return "  no structural change."
    order = {BREAKING: 0, ADDITIVE: 1, INFO: 2}
    return "\n".join(
        f"  [{f['severity']:<8}] {f['kind']:<22} {f['detail']}"
        for f in sorted(findings, key=lambda f: (order[f["severity"]], f["kind"]))
    )


def has_breaking(findings):
    return any(f["severity"] == BREAKING for f in findings)


def changelog(findings, from_version, to_version):
    """The structural changelog upstream does not publish.

    Emitted as data rather than text so it can be posted, diffed, or filed as
    an issue against upstream without reformatting.
    """
    return {
        "fromVersion": from_version,
        "toVersion": to_version,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generatedBy": "learning-net",
        "breaking": [f for f in findings if f["severity"] == BREAKING],
        "additive": [f for f in findings if f["severity"] == ADDITIVE],
        "info": [f for f in findings if f["severity"] == INFO],
    }
