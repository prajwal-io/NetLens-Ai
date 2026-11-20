import pytest
from fastapi import HTTPException

from app.services import url_check
from app.services.url_model import url_model
from app.services.url_probe import ProbeFailure, UnsafeDestination
from ml.url_features import FEATURES, extract_url_features


@pytest.mark.parametrize("value", [
    "javascript:alert(1)", "ftp://example.com/file", "https://user:secret@example.com/",
    "https://bad host.example/", "https://example.com:70000/", "https://bad_host.example/",
    "https://example.com\\@evil.example/", "https://[:::]/", "http://127.0.0.1/",
    "http://[::1]/", "https://example.com:8080/",
])
def test_url_normalization_rejects_invalid_or_nonpublic_destinations(value):
    with pytest.raises(HTTPException) as error:
        url_check.normalize_url(value)
    assert error.value.status_code == 422


def test_url_normalization_strips_credentials_fragment_and_default_port():
    assert url_check.normalize_url(" HTTPS://ExAmPle.com:443/path?q=1#secret ") == "https://example.com/path?q=1"
    assert url_check.normalize_url("https://example.com/") == "https://example.com"


def test_url_feature_extraction_is_stable_for_runtime_inference():
    first = extract_url_features("https://example.com/account/verify?id=2")
    second = extract_url_features("https://example.com/account/verify?id=2")
    assert first.shape == (len(FEATURES),)
    assert (first == second).all()


def test_shipped_url_model_runs_real_inference():
    result = url_model.predict("https://www.example.com/account/verify?id=2")
    assert result["model_version"] == "netsight-url-lr-phiusiil-v1"
    assert result["label"] in {"phishing_signal", "no_strong_signal"}
    assert 0 <= result["phishing_score"] <= 1
    assert 0 < result["threshold"] < 1


def test_shipped_model_sees_root_urls_in_the_same_form_as_training_data():
    result = url_model.predict(url_check.normalize_url("https://www.paypal.com/"))
    assert result["label"] == "no_strong_signal"


def test_live_probe_pins_public_dns_and_records_redirect_hosts(monkeypatch):
    resolved = []
    requested = []

    def addresses(host, port):
        resolved.append((host, port))
        return ["93.184.216.34"]

    def head(url, pinned):
        requested.append((url, pinned))
        if len(requested) == 1:
            return 302, "https://www.example.com/final"
        return 200, None

    monkeypatch.setattr(url_check, "_public_addresses", addresses)
    monkeypatch.setattr(url_check, "_head_once", head)
    result = url_check._probe("https://example.com/start")

    assert resolved == [("example.com", 443), ("www.example.com", 443)]
    assert all(addresses == ["93.184.216.34"] for _, addresses in requested)
    assert result["status"] == "reachable"
    assert result["http_status"] == 200
    assert result["dns_address_count"] == 2
    assert result["redirects"] == [{"status": 302, "from_host": "example.com", "to_host": "www.example.com", "cross_host": True}]


def test_encoded_newlines_cannot_inject_http_headers(monkeypatch):
    from app.services import url_probe

    class FakeSocket:
        request = b""

        def settimeout(self, _timeout):
            pass

        def sendall(self, content):
            self.request = content

        def recv(self, _size):
            return b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

        def close(self):
            pass

    fake = FakeSocket()
    monkeypatch.setattr(url_probe.socket, "create_connection", lambda *_args, **_kwargs: fake)
    assert url_probe._head_once("http://example.com/%0d%0aHost:evil", ["93.184.216.34"]) == (200, None)
    assert fake.request.startswith(b"HEAD /%0d%0aHost:evil HTTP/1.1\r\nHost: example.com\r\n")


def test_live_probe_blocks_private_dns_answers(monkeypatch):
    def private(_host, _port):
        raise UnsafeDestination("private_or_reserved_address")

    monkeypatch.setattr(url_check, "_public_addresses", private)
    with pytest.raises(UnsafeDestination):
        url_check._probe("https://example.com/")


def test_live_probe_reports_resolved_dns_when_http_is_unreachable(monkeypatch):
    def connection_failure(_url, _addresses):
        raise ProbeFailure("connection_failed")

    monkeypatch.setattr(url_check, "_public_addresses", lambda _host, _port: ["93.184.216.34"])
    monkeypatch.setattr(url_check, "_head_once", connection_failure)
    result = url_check._probe("https://example.com/")
    assert result == {"status": "unreachable", "http_status": None, "final_host": "example.com", "dns_address_count": 1, "redirects": []}


def test_url_model_and_reachability_are_separate_signals(monkeypatch):
    monkeypatch.setattr(url_check.url_model, "predict", lambda _url: {
        "model_version": "test-url-model", "label": "phishing_signal", "phishing_score": 0.9, "threshold": 0.5,
    })
    monkeypatch.setattr(url_check, "_probe", lambda _url: {
        "status": "unreachable", "http_status": None, "final_host": "example.com", "dns_address_count": 0, "redirects": [],
    })
    result = url_check.check_url("https://example.com/login")
    assert result["model"]["label"] == "phishing_signal"
    assert result["probe"]["status"] == "unreachable"
    assert result["stages"][-1]["name"] == "Evidence summary"
