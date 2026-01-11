"""打印 DEVMODE 处理测试 - Windows版本"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from app import printer as printer_mod
except Exception as e:  # pragma: no cover
    pytest.skip(f"win32 打印依赖不可用: {e}", allow_module_level=True)


class TestDevModeDocumentProperties:
    def test_document_properties_return_int_keeps_devmode(self, monkeypatch):
        devmode = object()

        def fake_document_properties(hwnd, hprinter, printer_name, out_devmode, in_devmode, mode):
            return 1

        monkeypatch.setattr(printer_mod.win32print, "DocumentProperties", fake_document_properties)

        result = printer_mod._driver_validate_devmode(object(), "Printer", devmode)
        assert result is devmode

    def test_document_properties_return_devmode_replaces(self, monkeypatch):
        class FakeDevMode:
            pass

        original = object()
        returned = FakeDevMode()

        def fake_document_properties(hwnd, hprinter, printer_name, out_devmode, in_devmode, mode):
            return returned

        monkeypatch.setattr(printer_mod.win32print, "DocumentProperties", fake_document_properties)
        monkeypatch.setattr(printer_mod.pywintypes, "DEVMODEType", FakeDevMode)

        result = printer_mod._driver_validate_devmode(object(), "Printer", original)
        assert result is returned

    def test_document_properties_exception_keeps_devmode(self, monkeypatch):
        devmode = object()

        def fake_document_properties(hwnd, hprinter, printer_name, out_devmode, in_devmode, mode):
            raise RuntimeError("boom")

        monkeypatch.setattr(printer_mod.win32print, "DocumentProperties", fake_document_properties)

        result = printer_mod._driver_validate_devmode(object(), "Printer", devmode)
        assert result is devmode

