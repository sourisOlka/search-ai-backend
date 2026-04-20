import pytest
import uuid
from datetime import datetime, timezone
from src.models import StoredFile, Alert
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_get_alerts_mock_data(client, mock_db_session):
    u_id = str(uuid.uuid4())
    
    test_alert = Alert(
        id=1,
        file_id=u_id,
        level="info",
        message="Test alert message",
        created_at=datetime.now(timezone.utc)
    )

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 1

    mock_result_data = MagicMock()
    mock_result_data.scalars.return_value.all.return_value = [test_alert]

    mock_db_session.execute.side_effect = [mock_result_count, mock_result_data]

    response = await client.get("/alerts")
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_alerts_pagination_mock(client, mock_db_session):
    u_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    fake_alerts = [
        Alert(id=i, file_id=u_id, level="info", message=f"Alert {i}", created_at=now)
        for i in range(2)
    ]

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 5

    mock_result_data = MagicMock()
    mock_result_data.scalars.return_value.all.return_value = fake_alerts

    mock_db_session.execute.side_effect = [mock_result_count, mock_result_data]

    response = await client.get("/alerts", params={"page": 1, "size": 2})
    
    assert response.status_code == 200
    data = response.json()

    assert len(data["alerts"]) == 2
    assert data["total_count"] == 5


@pytest.mark.asyncio
async def test_files_pagination_mock(client, mock_db_session):
    now = datetime.now(timezone.utc)
    
    fake_files = [
        StoredFile(
            id=str(uuid.uuid4()),
            title=f"Test File {i}",
            original_name=f"file_{i}.txt",
            stored_name=f"stored_{i}.txt",
            mime_type="text/plain",
            size=100,
            processing_status="processed",
            created_at=now,
            updated_at=now,
            requires_attention=False 
        ) for i in range(2)
    ]

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 3

    mock_result_data = MagicMock()
    mock_result_data.scalars.return_value.all.return_value = fake_files

    mock_db_session.execute.side_effect = [mock_result_count, mock_result_data]

    response = await client.get("/files", params={"page": 1, "size": 2})
    
    assert response.status_code == 200
    data = response.json()

    assert len(data["files"]) == 2
    assert data["total_count"] == 3

    assert data["files"][0]["requires_attention"] is False


@pytest.mark.asyncio
async def test_upload_file_api_mock(client, mock_db_session):

    mock_db_session.add = MagicMock()

    def mock_refresh_logic(obj):
        obj.id = str(uuid.uuid4())
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        obj.requires_attention = False
        obj.processing_status = "processed"

    mock_db_session.refresh = AsyncMock(side_effect=mock_refresh_logic)

    file_content = b"fake content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    data = {"title": "New File"}

    response = await client.post("/files", data=data, files=files)
    
    assert response.status_code in [200, 201]
    res_json = response.json()
    assert res_json["title"] == "New File"
    assert res_json["requires_attention"] is False

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
