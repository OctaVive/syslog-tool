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
    assert [participant["label"] for participant in flow["participants"]] == ["example.com", "52.114.75.24"]
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
    ok = next(step for step in ping["flow"]["steps"] if step["label"] == "200 OK")
    assert options["from_participant"] == ids["72.10.10.68"]
    assert options["to_participant"] == ids["10.183.57.1"]
    assert ok["from_participant"] == ids["10.183.57.1"]
    assert ok["to_participant"] == ids["72.10.10.68"]


@pytest.mark.asyncio
async def test_response_arrow_follows_outgoing_peer(client):
    content = """Oct 19 09:37:46.514 local3.notice [S=33454867] [SID=cb315a:67:7894027] (N 1) ---- Outgoing SIP Message to 62.140.143.68:5060 from SIPInterface #5 ----
SIP/2.0 200 OK
Via: SIP/2.0/UDP 62.140.143.68:5060;branch=z9hG4bKnd7vpc30bokcjc5df1o8.1
From: <sip:0615650031@10.183.57.1>;tag=SDv7loc01-2d92a69
To: <sip:04320726000@62.140.143.68>;tag=3a8ab50a
Call-ID: call-1@10.183.57.1
CSeq: 1 INVITE
Content-Length: 0
"""
    response = await client.post(
        "/api/uploads",
        files={"file": ("syslog.txt", content.encode(), "text/plain")},
    )
    assert response.status_code == 200
    session = response.json()["sessions"][0]
    ids = {participant["label"]: participant["id"] for participant in session["flow"]["participants"]}
    ok = next(step for step in session["flow"]["steps"] if step["label"] == "200 OK")
    assert ok["from_participant"] == ids["10.183.57.1"]
    assert ok["to_participant"] == ids["62.140.143.68"]


@pytest.mark.asyncio
async def test_invite_200_returns_to_invite_sender(client):
    content = """Oct 19 09:37:46.469 local3.notice [S=33454860] [SID=cb315a:67:7894027] (N 1) ---- Incoming SIP Message from 62.140.143.68:5060 to SIPInterface #5 ----
INVITE sip:04320726000@10.183.57.1 SIP/2.0
Via: SIP/2.0/UDP 62.140.143.68:5060;branch=z9hG4bKabc
From: <sip:0615650031@10.183.57.1>;tag=SDv7loc01-2d92a69
To: <sip:04320726000@62.140.143.68>
Call-ID: call-1@10.183.57.1
CSeq: 1 INVITE
Content-Length: 0

Oct 19 09:37:46.514 local3.notice [S=33454867] [SID=cb315a:67:7894027] (N 2) ---- Incoming SIP Message from 62.140.143.68:5060 to SIPInterface #5 ----
SIP/2.0 200 OK
Via: SIP/2.0/UDP 62.140.143.68:5060;branch=z9hG4bKabc
From: <sip:0615650031@10.183.57.1>;tag=SDv7loc01-2d92a69
To: <sip:04320726000@62.140.143.68>;tag=3a8ab50a
Call-ID: call-1@10.183.57.1
CSeq: 1 INVITE
Content-Length: 0
"""
    response = await client.post(
        "/api/uploads",
        files={"file": ("syslog.txt", content.encode(), "text/plain")},
    )
    assert response.status_code == 200
    session = response.json()["sessions"][0]
    ids = {participant["label"]: participant["id"] for participant in session["flow"]["participants"]}
    invite = next(step for step in session["flow"]["steps"] if step["label"] == "INVITE")
    ok = next(step for step in session["flow"]["steps"] if step["label"] == "200 OK")
    assert invite["from_participant"] == ids["62.140.143.68"]
    assert invite["to_participant"] == ids["10.183.57.1"]
    assert ok["from_participant"] == ids["10.183.57.1"]
    assert ok["to_participant"] == ids["62.140.143.68"]
