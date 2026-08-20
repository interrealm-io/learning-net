"""Query-layer and drift tests. The `mirror` fixture lives in conftest.py."""

import json

import pytest

from collective.graph import Graph
from collective.sync import Shape, diff_shapes, has_breaking


def test_code_is_not_unique_and_spine_sorts_first(mirror):
    r = mirror.find_standard("4.OA.A.3")
    assert r["matchCount"] == 2
    assert r["standards"][0]["jurisdiction"] == "Multi-State"
    assert r["note"]


def test_resolve_accepts_code_or_id(mirror):
    assert mirror.resolve("ca-1")[0]["id"] == "ca-1"
    assert mirror.resolve("4.OA.A.3")


def test_bare_code_resolves_to_spine_not_arbitrary_state(mirror):
    assert mirror.resolve("4.OA.A.3")[0]["jurisdiction"] == "Multi-State"


def test_components_accept_jurisdiction_to_disambiguate_code(mirror):
    r = mirror.learning_components("L.2.1", jurisdiction="California")
    assert r["standard"]["jurisdiction"] == "California"
    assert r["bridgedViaMultiState"] is True


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


def test_components_direct_do_not_bridge(mirror):
    r = mirror.learning_components("ca-1")
    assert r["componentCount"] == 1
    assert r["bridgedViaMultiState"] is False


def test_components_roll_up_from_child_standards(mirror):
    """Components attach to lettered children; asking the parent must find them."""
    r = mirror.learning_components("ms-ela")
    assert r["componentCount"] == 1
    c = r["learningComponents"][0]
    assert c["supportsStandard"] == "L.2.1.e"
    assert c["examples"] == ["Underlines big in 'The big dog barks.'"]


def test_components_bridge_state_through_spine(mirror):
    """A state standard with no direct component edges reaches the spine's."""
    r = mirror.learning_components("ca-ela")
    assert r["bridgedViaMultiState"] is True
    assert r["componentCount"] == 1
    assert "adjective" in r["learningComponents"][0]["component"]


def test_components_absent_is_reported_not_silent(mirror):
    r = mirror.learning_components("tx-1")
    assert r["componentCount"] == 0
    assert "search_learning_components" in r["note"]


def test_list_standards_facets_and_filters(mirror):
    r = mirror.list_standards(jurisdiction="California")
    assert r["totalCount"] == 2
    assert r["facets"]["subjects"] == {"English Language Arts": 1, "Mathematics": 1}
    assert r["facets"]["gradeLevels"] == {"2": 1, "4": 1}
    narrowed = mirror.list_standards(jurisdiction="california", grade_level="2")
    assert [s["statementCode"] for s in narrowed["standards"]] == ["L.2.1"]


def test_list_standards_reports_component_counts(mirror):
    by_code = {
        s["statementCode"]: s
        for s in mirror.list_standards(jurisdiction="California")["standards"]
    }
    assert by_code["4.OA.A.3"]["learningComponentCount"] == 1  # lc-1 supports ca-1
    assert "learningComponentCount" not in by_code["L.2.1"]  # reachable only by bridge


def test_list_standards_requires_a_filter(mirror):
    from collective.graph import GraphError

    with pytest.raises(GraphError):
        mirror.list_standards()


def test_search_components_maps_to_jurisdiction_via_hub(mirror):
    """lc-adj supports only the spine's L.2.1.e; California is two hops away."""
    r = mirror.search_learning_components("adjective", jurisdiction="California")
    assert r["resultCount"] == 1
    c = r["components"][0]
    assert c["viaMultiStateHub"] is True
    assert [s["statementCode"] for s in c["supportsStandards"]] == ["L.2.1"]
    assert c["examples"]


def test_search_components_labels_grade_relation(mirror):
    r = mirror.search_learning_components(
        "adjective", jurisdiction="California", grade_level="5"
    )
    assert r["components"][0]["gradeRelation"] == "below"
    assert "foundational" in r["note"]


def test_search_components_drops_and_counts_unmappable(mirror):
    """A jurisdiction the component cannot reach is reported, not silently empty."""
    r = mirror.search_learning_components("adjective", jurisdiction="Texas")
    assert r["resultCount"] == 0
    assert r["unmappedCount"] == 1
    assert "Texas" in r["note"]


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
    from collective.sync import export_url

    assert export_url("nodes.jsonl", "1.12.0") == (
        "https://cdn.learningcommons.org/knowledge-graph/v1.12.0/exports/"
        "nodes.jsonl?ref=collective"
    )


def test_fetch_downloads_both_exports(tmp_path, fake_cdn):
    from collective.sync import fetch

    got = fetch(tmp_path / "out", "1.12.0", base=fake_cdn, log=lambda *a, **k: None)
    assert set(got) == {"nodes.jsonl", "relationships.jsonl"}
    assert (tmp_path / "out" / "nodes.jsonl").read_text().strip()


def test_fetch_unknown_version_is_a_clear_error(tmp_path, fake_cdn):
    from collective.sync import fetch

    with pytest.raises(RuntimeError):
        fetch(tmp_path / "out", "9.9.9", base=fake_cdn, log=lambda *a, **k: None)


def test_discover_finds_newer_release(fake_cdn):
    from collective.sync import discover_versions

    assert discover_versions("1.12.0", base=fake_cdn) == "1.13.0"


def test_discover_returns_current_when_nothing_newer(fake_cdn):
    from collective.sync import discover_versions

    assert discover_versions("1.13.0", base=fake_cdn) == "1.13.0"


def test_build_records_upstream_version(tmp_path, fake_cdn):
    from collective.build import build
    from collective.sync import fetch, mirror_version

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
    from collective import build as buildmod
    from collective.build import build
    from collective.sync import fetch

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


# -- verify_alignment_claim -------------------------------------------------


def test_claim_addressable_when_code_exists_in_jurisdiction(mirror):
    r = mirror.verify_alignment_claim("4.OA.A.3", "California")
    assert r["verdict"] == "addressable"
    assert "Verified" in r["plainLanguage"]


def test_claim_not_addressable_in_texas_but_equivalent_found(mirror):
    """The flagship case: Texas never adopted the Common Core code."""
    r = mirror.verify_alignment_claim("4.OA.A.3", "Texas")
    assert r["verdict"] == "equivalent_exists"
    assert "NOT a standard in Texas" in r["plainLanguage"]
    assert [e["statementCode"] for e in r["localEquivalents"]] == ["111.6.b.5.A"]


def test_unknown_code_is_reported_as_uncheckable(mirror):
    r = mirror.verify_alignment_claim("9.ZZ.99", "Texas")
    assert r["verdict"] == "unknown_code"


def test_jurisdiction_name_is_matched_loosely(mirror):
    assert mirror.verify_alignment_claim("4.OA.A.3", "california")["verdict"] == "addressable"


def test_bad_jurisdiction_suggests_rather_than_erroring(mirror):
    r = mirror.verify_alignment_claim("4.OA.A.3", "Texass")
    assert r["verdict"] in ("unknown_jurisdiction", "equivalent_exists")


def test_browse_and_component_search_are_mcp_tools():
    from collective.server import TOOLS

    names = [t["name"] for t in TOOLS]
    assert "list_standards" in names
    assert "search_learning_components" in names


def test_verify_is_exposed_as_an_mcp_tool():
    from collective.server import TOOLS

    names = [t["name"] for t in TOOLS]
    assert "verify_alignment_claim" in names
    schema = next(t for t in TOOLS if t["name"] == "verify_alignment_claim")["inputSchema"]
    assert schema["required"] == ["statementCode", "jurisdiction"]


# -- coverage_report --------------------------------------------------------


def test_coverage_flags_jurisdictions_with_no_alignment(mirror):
    """A state with standards but no alignment edges is the finding that matters."""
    rep = mirror.coverage_report()
    by = {r["jurisdiction"]: r for r in rep["byJurisdiction"]}
    assert by["California"]["crosswalked"] == 2  # ca-1 and ca-ela
    assert by["California"]["isolated"] is False
    assert rep["national"]["jurisdictions"] == 3


def test_coverage_sorts_worst_first(mirror):
    rep = mirror.coverage_report()
    pcts = [r["crosswalkPct"] for r in rep["byJurisdiction"]]
    assert pcts == sorted(pcts)


def test_coverage_counts_all_four_dimensions(mirror):
    by = {r["jurisdiction"]: r for r in mirror.coverage_report()["byJurisdiction"]}
    ca = by["California"]
    assert ca["withComponents"] == 1        # lc-1 supports ca-1
    assert by["Multi-State"]["withCurriculum"] == 1   # les-1 aligns to ms-1
    assert by["Multi-State"]["withProgression"] == 2  # ms-0 buildsTowards ms-1


def test_coverage_subject_filter(mirror):
    assert mirror.coverage_report(subject="Mathematics")["national"]["standards"] == 4
    assert mirror.coverage_report(subject="Science")["national"]["standards"] == 0


def test_coverage_carries_provenance(mirror):
    assert mirror.coverage_report()["generatedFrom"]["source"] == "test"


def test_coverage_is_an_mcp_tool():
    from collective.server import TOOLS

    assert "coverage_report" in [t["name"] for t in TOOLS]
