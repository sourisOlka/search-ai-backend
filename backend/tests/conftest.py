import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from src.app import app
from src.database import get_db

@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    return mock

@pytest.fixture
async def client(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://testserver"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_example(client, mock_db_session):
    mock_result = MagicMock()
    mock_db_session.execute.return_value = mock_result
    response = await client.get("/some-endpoint")
    assert response.status_code == 200
    mock_db_session.execute.assert_called_once()
