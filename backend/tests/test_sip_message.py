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


def test_extract_uri_host():
    assert extract_uri_host("<sip:caller@example.com>;tag=abc") == "example.com"
    assert extract_uri_host("sip:10.0.0.1:5060") == "10.0.0.1"
