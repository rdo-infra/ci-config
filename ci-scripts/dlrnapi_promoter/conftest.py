import sys
import pytest

if sys.version_info < (3, 6):
    pytest.skip("Minimal version of python supported is 3.6", allow_module_level=True)
