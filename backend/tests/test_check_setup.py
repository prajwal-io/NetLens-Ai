from urllib.error import HTTPError

from scripts import check_setup


def test_setup_check_explains_unready_model_health_response(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["check_setup"])

    def unavailable(*args, **kwargs):
        raise HTTPError(args[0], 503, "Not ready", {}, None)

    monkeypatch.setattr(check_setup, "urlopen", unavailable)
    assert check_setup.main() == 1
    assert "evaluated model artifact" in capsys.readouterr().err
