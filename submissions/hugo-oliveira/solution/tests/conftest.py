import pytest

from lead_scorer import dados


@pytest.fixture(scope="session")
def base():
    return dados.carregar()
