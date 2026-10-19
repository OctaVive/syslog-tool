from pathlib import Path

from app.parsers.audiocodes_syslog import parse_file, parse_sip_events
from app.parsers.sip_message import parse_sip_message

FIXTURE = Path(__file__).parent / "fixtures" / "sample_audiocodes.syslog"
WEB_EXPORT = Path(__file__).parent / "fixtures" / "web_export_audiocodes.syslog"


def test_parse_syslog_file():
    with FIXTURE.open("rb") as handle:
        events, warnings = parse_file(handle)

    assert len(events) >= 6
    assert isinstance(warnings, list)

    sip_events = parse_sip_events(events)
    assert len(sip_events) == 6

    options = sip_events[0]
    assert options.sid == "50e91b:74:353424"
    assert options.sequence == 12614840
    assert "OPTIONS sip:" in options.sip_text

    invite_event = sip_events[1]
    assert invite_event.direction == "outgoing"
    assert invite_event.peer_ip == "52.114.75.24"
    assert invite_event.peer_port == 5061
    assert invite_event.sip_text.startswith("INVITE")
    assert "\n\nv=0" in invite_event.sip_text


def test_non_sip_event_has_no_sip_text():
    with FIXTURE.open("rb") as handle:
        events, _ = parse_file(handle)

    non_sip = [event for event in events if event.sid == "2ed1c8:96:5"]
    assert len(non_sip) == 1
    assert non_sip[0].sip_text is None


def test_web_export_syslog():
    with WEB_EXPORT.open("rb") as handle:
        events, warnings = parse_file(handle)

    assert len(events) == 14
    assert warnings == []

    sip_events = parse_sip_events(events)
    assert len(sip_events) == 9

    ha_disabled = next(event for event in events if "HA is disabled" in event.preamble)
    assert ha_disabled.sip_text is None
    assert ha_disabled.bid == "cb315a:67"
    assert ha_disabled.timestamp == "Oct 19 07:22:45.774"
    assert ha_disabled.device_ip == ""

    parse_errors = [event for event in events if "Parsing error" in event.preamble or "Parse error" in event.preamble]
    assert len(parse_errors) == 2
    assert all(event.sip_text is None for event in parse_errors)

    first_call = [event for event in sip_events if event.sid == "cb315a:67:7890786"]
    assert len(first_call) == 2
    outgoing = next(event for event in first_call if event.direction == "outgoing")
    incoming = next(event for event in first_call if event.direction == "incoming")
    assert outgoing.peer_ip == "192.168.11.220"
    assert outgoing.peer_port == 5060
    assert incoming.peer_ip == "192.168.11.220"
    assert incoming.peer_port == 5060

    parsed_outgoing = parse_sip_message(outgoing.sip_text or "")
    assert parsed_outgoing is not None
    assert parsed_outgoing.status_code == 200
    assert parsed_outgoing.method == "OPTIONS"
    assert parsed_outgoing.call_id == "2230b96a-c397-4c94-a42f-4abbe637b025"
    assert "[Time:" not in (outgoing.sip_text or "")

    parsed_incoming = parse_sip_message(incoming.sip_text or "")
    assert parsed_incoming is not None
    assert parsed_incoming.method == "OPTIONS"
    assert parsed_incoming.call_id == parsed_outgoing.call_id

    headerless = [event for event in sip_events if event.sid is None]
    assert len(headerless) == 1
    assert headerless[0].sequence == 33447657
    assert headerless[0].timestamp == "19-10 09:22:36.258"
    orphan = parse_sip_message(headerless[0].sip_text or "")
    assert orphan is not None
    assert orphan.status_code == 200
    assert orphan.method == "OPTIONS"
    assert orphan.call_id == "ed262f8538b46604aec827c775bfe9e1030000u6u3100@72.10.10.236"
