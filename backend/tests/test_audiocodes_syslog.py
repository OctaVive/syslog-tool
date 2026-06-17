from pathlib import Path

from app.parsers.audiocodes_syslog import parse_file, parse_sip_events

FIXTURE = Path(__file__).parent / "fixtures" / "sample_audiocodes.syslog"


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


def test_non_sip_event_has_no_sip_text():
    with FIXTURE.open("rb") as handle:
        events, _ = parse_file(handle)

    non_sip = [event for event in events if event.sid == "2ed1c8:96:5"]
    assert len(non_sip) == 1
    assert non_sip[0].sip_text is None
