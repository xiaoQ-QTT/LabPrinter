import pytest


def test_build_lp_command_options():
    from labprinter_linux.app.printer import build_lp_command

    cmd = build_lp_command(
        '/tmp/a.pdf',
        {
            'copies': 2,
            'page_range': '2-3',
            'duplex': 'two-sided-long-edge',
            'paper_size': 'A4',
            'color': 'grayscale',
        },
        printer_name='HP',
    )

    assert cmd[0].endswith('lp')
    assert '-d' in cmd and 'HP' in cmd
    assert ['-n', '2'] in [cmd[i:i + 2] for i in range(len(cmd) - 1)]
    assert 'page-ranges=2-3' in cmd
    assert 'sides=two-sided-long-edge' in cmd
    assert 'media=A4' in cmd
    assert 'print-color-mode=monochrome' in cmd
    assert cmd[-1] == '/tmp/a.pdf'


def test_page_range_rejects_bad_chars():
    from labprinter_linux.app.printer import build_lp_command

    with pytest.raises(RuntimeError):
        build_lp_command('/tmp/a.pdf', {'page_range': '1;rm -rf /'}, printer_name='HP')


def test_print_requires_default_or_selection(monkeypatch, tmp_path):
    import labprinter_linux.app.printer as printer_mod

    file_path = tmp_path / "a.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(printer_mod.config, "DEFAULT_PRINTER", None)
    monkeypatch.setattr(printer_mod.config, "ALLOWED_PRINTERS", None)
    monkeypatch.setattr(printer_mod, "get_default_printer", lambda: None)
    monkeypatch.setattr(printer_mod, "get_printer_names", lambda: {"HP", "Canon"})

    with pytest.raises(RuntimeError) as e:
        printer_mod.print_file(str(file_path), {"copies": 1})
    assert "未设置默认打印机" in str(e.value)
