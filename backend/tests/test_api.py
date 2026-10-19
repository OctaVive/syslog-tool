from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "sample_audiocodes.syslog"
WEB_EXPORT = Path(__file__).parent / "fixtures" / "web_export_audiocodes.syslog"


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
async def test_upload_returns_sessions_and_stores_nothing(client):
    content = FIXTURE.read_bytes()
    response = await client.post(
        "/api/uploads",
        files={"file": ("sample.syslog", content, "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_count"] == 2
    assert payload["message_count"] == 6

    missing = await client.get(f"/api/uploads/{payload['id']}")
    assert missing.status_code == 404
    missing_sessions = await client.get(f"/api/uploads/{payload['id']}/sessions")
    assert missing_sessions.status_code == 404

    invite_session = next(item for item in payload["sessions"] if item["message_count"] == 5)
    assert invite_session["call_id"] == "call-flow-123@sbc11.example.com"
    flow = invite_session["flow"]
    assert len(flow["steps"]) == 5
    assert [participant["label"] for participant in flow["participants"]] == ["example.com"]
    assert any(step["label"] == "INVITE" for step in flow["steps"])
    assert any(message["raw_text"].startswith("INVITE") for message in invite_session["messages"])


@pytest.mark.asyncio
async def test_web_export_groups_headerless_sip_by_call_id(client):
    content = WEB_EXPORT.read_bytes()
    response = await client.post(
        "/api/uploads",
        files={"file": ("syslog.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["message_count"] == 9
    assert payload["session_count"] == 5

    session_list = payload["sessions"]
    headerless = next(item for item in session_list if item["sid"].startswith("call:"))
    assert headerless["call_id"] == "ed262f8538b46604aec827c775bfe9e1030000u6u3100@72.10.10.236"
    assert headerless["message_count"] == 1

    flow_data = headerless["flow"]
    assert [participant["label"] for participant in flow_data["participants"]] == ["72.10.10.236"]
    assert flow_data["steps"][0]["from_participant"] == flow_data["steps"][0]["to_participant"]

    ping = next(item for item in session_list if item["sid"] == "cb315a:67:7890785")
    labels = [participant["label"] for participant in ping["flow"]["participants"]]
    assert labels == ["72.10.10.68", "10.183.57.1"]
    ids = {participant["label"]: participant["id"] for participant in ping["flow"]["participants"]}
    options = next(step for step in ping["flow"]["steps"] if step["label"] == "OPTIONS")
    ok = next(step for step in ping["flow"]["steps"] if step["label"] == "200")
    assert options["from_participant"] == ids["72.10.10.68"]
    assert options["to_participant"] == ids["10.183.57.1"]
    assert ok["from_participant"] == ids["10.183.57.1"]
    assert ok["to_participant"] == ids["72.10.10.68"]
