from app.parsers.sip_message import extract_uri_host, parse_sip_message

INVITE = """INVITE sip:user@example.com SIP/2.0
Via: SIP/2.0/TLS sbc.example.com:5061;branch=z9hG4bK1
From: <sip:caller@example.com>;tag=abc
To: <sip:user@example.com>
Call-ID: test-call-id
CSeq: 1 INVITE
Content-Length: 0
"""

RESPONSE = """SIP/2.0 200 OK
Via: SIP/2.0/TLS sbc.example.com:5061;branch=z9hG4bK1
From: <sip:caller@example.com>;tag=abc
To: <sip:user@example.com>;tag=def
Call-ID: test-call-id
CSeq: 1 INVITE
Content-Length: 0
"""


def test_parse_invite():
    parsed = parse_sip_message(INVITE)
    assert parsed is not None
    assert parsed.is_request is True
    assert parsed.method == "INVITE"
    assert parsed.call_id == "test-call-id"
    assert parsed.from_header.startswith("<sip:caller@example.com>")


def test_parse_response():
    parsed = parse_sip_message(RESPONSE)
    assert parsed is not None
    assert parsed.is_request is False
    assert parsed.status_code == 200
    assert parsed.method == "INVITE"


def test_cseq_method_is_not_the_sequence_number():
    parsed = parse_sip_message(
        "SIP/2.0 200 OK\nVia: SIP/2.0/UDP 192.168.11.220:5060;branch=z9hG4bK1\n"
        "From: sip:ping@192.168.11.220;tag=abc\nTo: sip:192.168.11.220;tag=def\n"
        "Call-ID: call-1\nCSeq: 26860 OPTIONS\nContent-Length: 0\n"
    )
    assert parsed is not None
    assert parsed.method == "OPTIONS"
    assert parsed.cseq == "26860 OPTIONS"


def test_inline_status_line_with_trailing_syslog_text():
    text = """Oct 19 10:29:47 local0.notice [S=4192745643] [SID=cdf4a74:24:955561055] SIP/2.0 100 Trying  Via: SIP/2.0/UDP 10.68.32.70:5060;branch=z9hG4bKac827601930
From: <sip:+31000000000@10.68.32.70;user=phone>;tag=1c2089274692
To: <sip:+31000000001@10.68.32.70;user=phone>;tag=1c999
Call-ID: 127461224119102826102949@10.68.32.70
CSeq: 1 INVITE
Server: VFNL-AC-SIP-MC-ESBC-V1.10
Content-Length: 0
(N 82714352) SIPLadder::FillVQData - Sending CallFlow message. SesSeq=2 Direction=Tx
(N 82714353) SETUP_EV: (#6797)SIPSbCCalleg -> (#3731)SBCall[NewCall->Initiated]
"""
    from app.parsers.audiocodes_syslog import parse_file, parse_sip_events
    from io import BytesIO

    events, _warnings = parse_file(BytesIO(text.encode()))
    sip_events = parse_sip_events(events)
    assert len(sip_events) == 1
    parsed = parse_sip_message(sip_events[0].sip_text or "")
    assert parsed is not None
    assert parsed.status_code == 100
    assert parsed.method == "INVITE"
    assert parsed.call_id == "127461224119102826102949@10.68.32.70"
    assert parsed.via is not None and parsed.via.startswith("SIP/2.0/UDP 10.68.32.70:5060")
    assert "(N 82714352)" not in parsed.raw_text


def test_extract_uri_host():
    assert extract_uri_host("<sip:caller@example.com>;tag=abc") == "example.com"
    assert extract_uri_host("sip:10.0.0.1:5060") == "10.0.0.1"
