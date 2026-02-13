from historia_bot.ai import _is_wsl, _wsl_windows_host_ip


def test_wsl_windows_host_ip_from_resolv_conf(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("# comment\nnameserver 172.22.224.1\n", encoding="utf-8")
    assert _wsl_windows_host_ip(str(resolv)) == "172.22.224.1"


def test_is_wsl_detects_microsoft_kernel(tmp_path):
    osrelease = tmp_path / "osrelease"
    osrelease.write_text("5.15.167.4-microsoft-standard-WSL2", encoding="utf-8")
    assert _is_wsl(str(osrelease)) is True
