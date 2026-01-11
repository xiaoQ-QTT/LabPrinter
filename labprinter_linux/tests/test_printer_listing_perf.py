import pytest


class DummyResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_get_printers_uses_single_lpstat_o(monkeypatch):
    import labprinter_linux.app.printer as printer_mod

    # 清空缓存，保证本测试可控
    printer_mod._DEFAULT_PRINTER_CACHE = None
    printer_mod._PRINTER_NAMES_CACHE = None
    printer_mod._JOBS_COUNT_CACHE = None

    monkeypatch.setattr(printer_mod.config, "DEFAULT_PRINTER", "HP")
    monkeypatch.setattr(printer_mod.config, "ALLOWED_PRINTERS", None)

    calls = []

    def fake_run_cmd(cmd, timeout):
        calls.append(cmd)
        if cmd[1] == "-p":
            return DummyResult(
                0,
                "printer HP is idle. enabled since ...\n"
                "printer Canon is idle. enabled since ...\n",
                "",
            )
        if cmd[1] == "-o":
            return DummyResult(
                0,
                "HP-123 user 1024 ...\n"
                "HP-124 user 1024 ...\n"
                "Canon-55 user 1024 ...\n",
                "",
            )
        if cmd[1] == "-d":
            return DummyResult(0, "system default destination: HP\n", "")
        raise AssertionError(f"unexpected cmd: {cmd}")

    monkeypatch.setattr(printer_mod, "_run_cmd", fake_run_cmd)

    printers = printer_mod.get_printers()
    assert {p["name"] for p in printers} == {"HP", "Canon"}
    jobs = {p["name"]: p["jobs"] for p in printers}
    assert jobs["HP"] == 2
    assert jobs["Canon"] == 1

    # 只允许 1 次 lpstat -p + 1 次 lpstat -o，不应按打印机逐个调用 lpstat -o <printer>
    assert calls.count([printer_mod.config.LPSTAT_COMMAND, "-p"]) == 1
    assert calls.count([printer_mod.config.LPSTAT_COMMAND, "-o"]) == 1


def test_allowed_printers_filters_list_and_validation(monkeypatch):
    import labprinter_linux.app.printer as printer_mod

    printer_mod._PRINTER_NAMES_CACHE = None
    printer_mod._JOBS_COUNT_CACHE = None
    monkeypatch.setattr(printer_mod.config, "DEFAULT_PRINTER", "HP")
    monkeypatch.setattr(printer_mod.config, "ALLOWED_PRINTERS", ["HP"])

    def fake_run_cmd(cmd, timeout):
        if cmd[1] == "-p":
            return DummyResult(0, "printer HP is idle.\nprinter Canon is idle.\n", "")
        if cmd[1] == "-o":
            return DummyResult(0, "HP-1 user ...\nCanon-2 user ...\n", "")
        raise AssertionError(f"unexpected cmd: {cmd}")

    monkeypatch.setattr(printer_mod, "_run_cmd", fake_run_cmd)

    printers = printer_mod.get_printers()
    assert [p["name"] for p in printers] == ["HP"]
    assert printer_mod.validate_printer_name("HP") is True
    assert printer_mod.validate_printer_name("Canon") is False


def test_default_printer_is_cached(monkeypatch):
    import labprinter_linux.app.printer as printer_mod

    printer_mod._DEFAULT_PRINTER_CACHE = None

    calls = []
    now = {"t": 100.0}

    def fake_monotonic():
        return now["t"]

    def fake_run_cmd(cmd, timeout):
        calls.append(cmd)
        return DummyResult(0, "system default destination: HP\n", "")

    monkeypatch.setattr(printer_mod.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(printer_mod, "_run_cmd", fake_run_cmd)

    assert printer_mod.get_default_printer() == "HP"
    assert printer_mod.get_default_printer() == "HP"
    assert calls.count([printer_mod.config.LPSTAT_COMMAND, "-d"]) == 1

    now["t"] = 200.0
    assert printer_mod.get_default_printer() == "HP"
    assert calls.count([printer_mod.config.LPSTAT_COMMAND, "-d"]) == 2

