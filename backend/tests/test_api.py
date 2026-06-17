from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "sample_audiocodes.syslog"


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_and_sessions(client):
    content = FIXTURE.read_bytes()
    response = await client.post(
        "/api/uploads",
        files={"file": ("sample.syslog", content, "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_count"] == 2
    assert payload["message_count"] == 6

    upload_id = payload["id"]
    sessions = await client.get(f"/api/uploads/{upload_id}/sessions")
    assert sessions.status_code == 200
    session_list = sessions.json()
    assert len(session_list) == 2

    invite_session = next(item for item in session_list if item["message_count"] == 5)
    detail = await client.get(f"/api/sessions/{invite_session['id']}")
    assert detail.status_code == 200
    assert detail.json()["call_id"] == "call-flow-123@sbc11.example.com"

    flow = await client.get(f"/api/sessions/{invite_session['id']}/flow")
    assert flow.status_code == 200
    flow_data = flow.json()
    assert len(flow_data["steps"]) == 5
    assert len(flow_data["participants"]) >= 2

    export = await client.get(f"/api/sessions/{invite_session['id']}/flow/export")
    assert export.status_code == 200
    assert "INVITE" in export.json()["text"]
