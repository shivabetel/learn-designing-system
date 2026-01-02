# def test_string():
#     name = "pytest"
#     assert name.upper() == "PYTEST"

import pytest


@pytest.fixture
def sample_data():
    return {"user": "shiva", "role": "admin"}


def test_user_role(sample_data):
    assert sample_data["role"] == "admin"
