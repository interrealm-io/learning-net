"""The HTTP API is the MCP handler table served over GET — not a second
implementation. These tests run the real server on an ephemeral port against
the synthetic mirror and check that payloads, bridging flags, and errors all
survive the transport.
"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from learningnet.server import _prune
from learningnet.web import make_server


@pytest.fixture
def served(mirror):
    srv = make_server(mirror.db_path, host="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, json.loads(r.read())


def test_api_answers_match_graph(served, mirror):
    status, body = _get(f"{served}/api/find_standard?statementCode=4.OA.A.3")
    assert status == 200
    assert body == _prune(mirror.find_standard("4.OA.A.3"))


def test_bridging_flags_survive_transport(served):
    _, body = _get(f"{served}/api/get_progression?standard=ca-1")
    assert body["bridgedViaMultiState"] is True
    assert body["progression"][0]["statementCode"] == "3.OA.A.1"


def test_int_params_are_coerced(served):
    status, body = _get(f"{served}/api/find_standard?statementCode=4.OA.A.3&limit=1")
    assert status == 200
    assert body["matchCount"] == 1


def test_unknown_tool_is_404(served):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{served}/api/no_such_tool")
    assert e.value.code == 404


def test_bad_reference_is_400_with_json_error(served):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{served}/api/get_progression?standard=zzz")
    assert e.value.code == 400
    assert "error" in json.loads(e.value.read())


def test_unexpected_param_is_400_not_crash(served):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{served}/api/graph_stats?bogus=1")
    assert e.value.code == 400


def test_concurrent_requests_do_not_break_sqlite(served):
    """The detail page fires five fetches at once; a shared connection across
    server threads raised sqlite3.InterfaceError. Regression for that."""
    import concurrent.futures

    urls = [
        f"{served}/api/get_standard_context?standard=ca-1",
        f"{served}/api/get_progression?standard=ca-1",
        f"{served}/api/get_progression?standard=ca-1&direction=forward",
        f"{served}/api/find_curriculum?standard=ca-1",
        f"{served}/api/get_learning_components?standard=ca-1",
    ] * 4
    with concurrent.futures.ThreadPoolExecutor(10) as ex:
        codes = list(ex.map(lambda u: urllib.request.urlopen(u).status, urls))
    assert codes == [200] * len(urls)


def test_static_serves_app_shell(served):
    from importlib import resources

    if not (resources.files("learningnet") / "static" / "index.html").is_file():
        pytest.skip("web bundle not built yet")
    with urllib.request.urlopen(f"{served}/") as r:
        assert r.status == 200
        assert b"<!doctype html" in r.read().lower()


def test_path_traversal_never_escapes_the_bundle(served):
    """Literal or percent-encoded, a `..` path must never reach repo files.

    Unknown paths may legitimately return the app shell (SPA fallback), so the
    assertion is on content, not status: pyproject.toml must not leak.
    """
    import http.client

    host, port = served.removeprefix("http://").split(":")
    for target in ("/../pyproject.toml", "/..%2f..%2fpyproject.toml"):
        conn = http.client.HTTPConnection(host, int(port))
        conn.request("GET", target)  # raw path — urllib would normalize the ..
        body = conn.getresponse().read()
        conn.close()
        assert b"[project]" not in body
