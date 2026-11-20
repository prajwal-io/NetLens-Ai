import httpx
import pytest

from scripts.migrate_sqlite_to_supabase import transfer_analysis


def test_transfer_analysis_preserves_owner_and_is_idempotent():
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/analyses"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/rpc/save_analysis"):
            return httpx.Response(200, json={})
        return httpx.Response(201, json=[])

    transport = httpx.MockTransport(respond)
    analysis = {"analysis_id": "a1", "total_flows": 1}
    copied = transfer_analysis(httpx.Client(transport=transport, base_url="https://project.test"),
                               "a1", "2a17d1c4-b2a8-4da5-976d-f5d46078b756", analysis,
                               [{"dur": 0.1}], [{"row_id": 1, "decision": "dismissed", "decided_at": "2026-11-19T00:00:00Z"}])

    assert copied is True
    assert requests[0].url.params["user_id"] == "eq.2a17d1c4-b2a8-4da5-976d-f5d46078b756"
    assert requests[1].url.path.endswith("/rpc/save_analysis")
    assert requests[1].read().decode().find('"p_user_id":"2a17d1c4-b2a8-4da5-976d-f5d46078b756"') >= 0
    assert requests[2].url.params["on_conflict"] == "analysis_id,user_id,row_id"


def test_transfer_analysis_rejects_missing_flow_data_before_writing():
    with httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail("must not make a request")),
                      base_url="https://project.test") as client:
        with pytest.raises(ValueError, match="incomplete or inconsistent"):
            transfer_analysis(client, "a1", "2a17d1c4-b2a8-4da5-976d-f5d46078b756",
                              {"analysis_id": "a1", "total_flows": 2}, [{"dur": 0.1}], [])


def test_transfer_analysis_does_not_replace_existing_analysis_or_decisions():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=[{"analysis_id": "a1"}] if request.url.path.endswith("/analyses") else [])

    transport = httpx.MockTransport(respond)
    with httpx.Client(transport=transport, base_url="https://project.test") as client:
        copied = transfer_analysis(client, "a1", "2a17d1c4-b2a8-4da5-976d-f5d46078b756",
                                   {"analysis_id": "a1", "total_flows": 1}, [{"dur": 0.1}],
                                   [{"row_id": 1, "decision": "dismissed", "decided_at": "2026-11-19T00:00:00Z"}])

    assert copied is False
    assert all(not request.url.path.endswith("/rpc/save_analysis") for request in requests)
    assert requests[-1].headers["prefer"] == "resolution=ignore-duplicates,return=minimal"
