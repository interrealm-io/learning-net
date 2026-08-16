"""Query-layer and drift tests. The `mirror` fixture lives in conftest.py."""

import json

import pytest

from learningnet.graph import Graph
from learningnet.sync import Shape, diff_shapes, has_breaking


def test_code_is_not_unique_and_spine_sorts_first(mirror):
    r = mirror.find_standard("4.OA.A.3")
    assert r["matchCount"] == 2
    assert r["standards"][0]["jurisdiction"] == "Multi-State"
    assert r["note"]


def test_resolve_accepts_code_or_id(mirror):
    assert mirror.resolve("ca-1")[0]["id"] == "ca-1"
    assert mirror.resolve("4.OA.A.3")


def test_progression_bridges_state_through_spine(mirror):
    """The whole reason this project exists: a one-hop query returns nothing."""
    r = mirror.progression("ca-1", "backward")
    assert r["bridgedViaMultiState"] is True
    assert r["resultCount"] == 1
    assert r["progression"][0]["statementCode"] == "3.OA.A.1"


def test_progression_on_spine_does_not_bridge(mirror):
    r = mirror.progression("ms-1", "backward")
    assert r["bridgedViaMultiState"] is False
    assert r["resultCount"] == 1


def test_progression_absent_is_reported_not_silent(mirror):
    r = mirror.progression("ms-0", "backward")
    assert r["resultCount"] == 0
    assert "authored only for Multi-State" in r["note"]


def test_crosswalk_state_to_state_is_two_hop(mirror):
    r = mirror.crosswalk("ca-1", to_jurisdiction="Texas")
    assert r["viaMultiStateHub"] is True
    assert [a["id"] for a in r["alignedStandards"]] == ["tx-1"]


def test_curriculum_bridges_to_spine(mirror):
    r = mirror.curriculum("ca-1")
    assert r["bridgedViaMultiState"] is True
    assert r["itemCount"] == 1
    assert r["curriculum"][0]["type"] == "Lesson"


def test_components_do_not_bridge(mirror):
    r = mirror.learning_components("ca-1")
    assert r["componentCount"] == 1


def test_search_is_literal_not_fts_syntax(mirror):
    """User text must never be interpreted as FTS5 query syntax."""
    assert mirror.search_standards("multistep word problems")["resultCount"] >= 1
    assert mirror.search_standards("products OR (whole")["resultCount"] >= 0


def test_stats_reports_provenance(mirror):
    assert mirror.stats()["snapshot"]["source"] == "test"


# -- drift ------------------------------------------------------------------


def _shape(labels, edges, props=None):
    s = Shape()
    s.node_labels.update(labels)
    s.edge_labels.update(edges)
    for lab, keys in (props or {}).items():
        s.props[lab].update(keys)
    return s


def test_removed_edge_type_is_breaking():
    old = _shape({"A": 10}, {"supports": 5})
    new = _shape({"A": 10}, {})
    f = diff_shapes(old, new)
    assert has_breaking(f)
    assert any(x["kind"] == "edge-type-removed" for x in f)


def test_added_label_is_additive_not_breaking():
    f = diff_shapes(_shape({"A": 10}, {}), _shape({"A": 10, "B": 3}, {}))
    assert not has_breaking(f)
    assert any(x["kind"] == "node-label-added" for x in f)


def test_property_disappearing_is_breaking():
    old = _shape({"A": 10}, {}, {"A": {"statementCode": 10}})
    new = _shape({"A": 10}, {}, {"A": {}})
    f = diff_shapes(old, new)
    assert has_breaking(f)
    assert any(x["kind"] == "property-removed" for x in f)


def test_identical_shapes_are_quiet():
    s = _shape({"A": 10}, {"supports": 5}, {"A": {"k": 10}})
    assert diff_shapes(s, _shape({"A": 10}, {"supports": 5}, {"A": {"k": 10}})) == []


# -- versioned fetch against a file:// CDN ----------------------------------


@pytest.fixture
def fake_cdn(tmp_path):
    """A stand-in CDN laid out exactly like Learning Commons'.

    Lets the whole init path — url shape, fetch, version probing — be exercised
    with no network, which is the only way it gets tested at all.
    """
    import shutil

    src = tmp_path / "src"
    src.mkdir()
    (src / "nodes.jsonl").write_text(
        json.dumps({"type": "node", "identifier": "n1",
                    "labels": ["StandardsFrameworkItem"],
                    "properties": {"statementCode": "1.A", "jurisdiction": "Multi-State"}}) + "\n"
    )
    (src / "relationships.jsonl").write_text("")
    root = tmp_path / "cdn"
    for v in ("1.12.0", "1.12.1", "1.13.0"):
        d = root / "knowledge-graph" / f"v{v}" / "exports"
        d.mkdir(parents=True)
        for f in ("nodes.jsonl", "relationships.jsonl"):
            shutil.copy(src / f, d / f)
    return f"file://{root}"


def test_export_url_matches_upstream_layout():
    from learningnet.sync import export_url

    assert export_url("nodes.jsonl", "1.12.0") == (
        "https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/"
        "nodes.jsonl?ref=learning-net"
    )


def test_fetch_downloads_both_exports(tmp_path, fake_cdn):
    from learningnet.sync import fetch

    got = fetch(tmp_path / "out", "1.12.0", base=fake_cdn, log=lambda *a, **k: None)
    assert set(got) == {"nodes.jsonl", "relationships.jsonl"}
    assert (tmp_path / "out" / "nodes.jsonl").read_text().strip()


def test_fetch_unknown_version_is_a_clear_error(tmp_path, fake_cdn):
    from learningnet.sync import fetch

    with pytest.raises(RuntimeError):
        fetch(tmp_path / "out", "9.9.9", base=fake_cdn, log=lambda *a, **k: None)


def test_discover_finds_newer_release(fake_cdn):
    from learningnet.sync import discover_versions

    assert discover_versions("1.12.0", base=fake_cdn) == "1.13.0"


def test_discover_returns_current_when_nothing_newer(fake_cdn):
    from learningnet.sync import discover_versions

    assert discover_versions("1.13.0", base=fake_cdn) == "1.13.0"


def test_build_records_upstream_version(tmp_path, fake_cdn):
    from learningnet.build import build
    from learningnet.sync import fetch, mirror_version

    exp = tmp_path / "e"
    fetch(exp, "1.12.0", base=fake_cdn, log=lambda *a, **k: None)
    db = tmp_path / "kg.sqlite"
    prov = build(str(exp), str(db), kg_version="1.12.0", log=lambda *a, **k: None)
    assert prov["kgVersion"] == "1.12.0"
    assert mirror_version(str(db)) == "1.12.0"


def test_interrupted_build_does_not_corrupt_the_live_mirror(tmp_path, fake_cdn, monkeypatch):
    """A killed build must leave the previous mirror intact and queryable.

    Regression: the build ran in place with journal_mode=OFF, so an interrupted
    run produced a corrupt file that the NEXT build could not open either.
    """
    from learningnet import build as buildmod
    from learningnet.build import build
    from learningnet.sync import fetch

    exp = tmp_path / "e"
    fetch(exp, "1.12.0", base=fake_cdn, log=lambda *a, **k: None)
    db = tmp_path / "kg.sqlite"
    build(str(exp), str(db), kg_version="1.12.0", log=lambda *a, **k: None)
    before = db.read_bytes()

    def boom(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(buildmod, "_ingest", boom)
    with pytest.raises(KeyboardInterrupt):
        build(str(exp), str(db), kg_version="9.9.9", log=lambda *a, **k: None)

    assert db.read_bytes() == before, "live mirror was modified by a failed build"
    assert Graph(str(db)).stats()["snapshot"]["kgVersion"] == "1.12.0"
