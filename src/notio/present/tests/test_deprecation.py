"""notio.present warns on import (deprecated 2026-11-24)."""
import importlib

import pytest


def test_import_warns_deprecated():
    import notio.present

    with pytest.warns(DeprecationWarning, match="notio.present is deprecated"):
        importlib.reload(notio.present)
