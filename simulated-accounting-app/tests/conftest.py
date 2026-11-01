import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "accounting.db")


@pytest.fixture
def client(db_path):
    return create_app(db_path).test_client()
