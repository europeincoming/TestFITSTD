"""Proxy PyMuPDF's fitz module and patch rebuild_site at runtime."""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import sys


def _load_real_fitz():
    try:
        return importlib.import_module("pymupdf")
    except Exception:
        search_path = [p for p in sys.path[1:] if p]
        spec = importlib.machinery.PathFinder.find_spec("fitz", search_path)
        if spec is None or spec.loader is None:
            raise ImportError("Unable to locate the real fitz module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


_REAL_FITZ = _load_real_fitz()

for _name in dir(_REAL_FITZ):
    if _name.startswith("__") and _name not in {"__doc__", "__all__", "__version__"}:
        continue
    globals()[_name] = getattr(_REAL_FITZ, _name)


def _trace(frame, event, arg):
    if event != "line":
        return _trace
    if frame.f_globals.get("__name__") != "__main__":
        return _trace
    if not frame.f_code.co_filename.endswith("rebuild_site.py"):
        return _trace
    module = sys.modules.get("__main__")
    if module is None:
        return _trace
    if getattr(module, "_enhanced_rebuild_patched", False):
        sys.settrace(None)
        return None
    if "main" not in module.__dict__:
        return _trace

    import enhanced_rebuild_runtime

    enhanced_rebuild_runtime.patch_module(module)
    module._enhanced_rebuild_patched = True
    sys.settrace(None)
    return None


sys.settrace(_trace)
