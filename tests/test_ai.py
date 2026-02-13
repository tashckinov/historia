from historia_bot.ai import _is_wsl, _parse_articles, _wsl_windows_host_ip


def test_wsl_windows_host_ip_from_resolv_conf(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("# comment\nnameserver 172.22.224.1\n", encoding="utf-8")
    assert _wsl_windows_host_ip(str(resolv)) == "172.22.224.1"


def test_is_wsl_detects_microsoft_kernel(tmp_path):
    osrelease = tmp_path / "osrelease"
    osrelease.write_text("5.15.167.4-microsoft-standard-WSL2", encoding="utf-8")
    assert _is_wsl(str(osrelease)) is True


def test_parse_articles_from_clean_json():
    raw = '{"articles":[{"title":"A","description":"B"}]}'
    assert _parse_articles(raw) == [{"title": "A", "description": "B"}]


def test_parse_articles_from_fenced_json_block():
    raw = 'Вот ответ\n```json\n{"articles":[{"title":"A","description":"B"}]}\n```'
    assert _parse_articles(raw) == [{"title": "A", "description": "B"}]


def test_parse_articles_returns_empty_on_invalid_json():
    raw = '{"articles": [{"title" "bad"}]}'
    assert _parse_articles(raw) == []
