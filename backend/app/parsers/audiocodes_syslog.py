from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import BinaryIO, Iterator, TextIO

SIP_METHODS = (
    "INVITE",
    "ACK",
    "BYE",
    "CANCEL",
    "OPTIONS",
    "REGISTER",
    "INFO",
    "UPDATE",
    "REFER",
    "NOTIFY",
    "SUBSCRIBE",
    "MESSAGE",
    "PRACK",
)

SYSLOG_HEADER_RE = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s*"
    r"[: ]?\s*"
    r"([\d.]+)\s*"
    r"[: ]?\s*"
    r"([\w.]+)\s*"
    r"[: ]?\s*"
    r"\[S=(\d+)\]\s*"
    r"(?:\[SID[=:]([^\]]+)\])?\s*"
    r"(?:\[BID[=:]([^\]]+)\])?\s*"
    r"(.*)$",
    re.IGNORECASE,
)

SIP_REQUEST_RE = re.compile(
    rf"^({'|'.join(SIP_METHODS)})\s+",
    re.IGNORECASE,
)
SIP_RESPONSE_RE = re.compile(r"^SIP/2\.0\s+(\d{3})\s+", re.IGNORECASE)
DIRECTION_RE = re.compile(
    r"----\s*(Incoming|Outgoing)\s+SIP\s+Message\s+(?:from|to)\s+([\d.]+):(\d+)",
    re.IGNORECASE,
)


@dataclass
class ParsedEvent:
    timestamp: str
    device_ip: str
    severity: str
    sequence: int
    sid: str | None
    bid: str | None
    preamble: str
    direction: str | None = None
    peer_ip: str | None = None
    peer_port: int | None = None
    sip_text: str | None = None
    raw_lines: list[str] = field(default_factory=list)


def _is_syslog_header(line: str) -> bool:
    return bool(SYSLOG_HEADER_RE.match(line.strip()))


def _extract_direction(preamble: str) -> tuple[str | None, str | None, int | None]:
    match = DIRECTION_RE.search(preamble)
    if not match:
        return None, None, None
    direction = match.group(1).lower()
    return direction, match.group(2), int(match.group(3))


def _find_sip_start_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if SIP_REQUEST_RE.match(stripped) or SIP_RESPONSE_RE.match(stripped):
            return index
    return None


def _extract_sip_text(lines: list[str]) -> str | None:
    start = _find_sip_start_index(lines)
    if start is None:
        return None
    return "\n".join(lines[start:]).strip()


def _parse_event_header(line: str) -> ParsedEvent | None:
    match = SYSLOG_HEADER_RE.match(line.strip())
    if not match:
        return None
    preamble = match.group(7).strip()
    direction, peer_ip, peer_port = _extract_direction(preamble)
    return ParsedEvent(
        timestamp=match.group(1),
        device_ip=match.group(2),
        severity=match.group(3),
        sequence=int(match.group(4)),
        sid=match.group(5),
        bid=match.group(6),
        preamble=preamble,
        direction=direction,
        peer_ip=peer_ip,
        peer_port=peer_port,
        raw_lines=[line.rstrip("\n\r")],
    )


def _finalize_event(event: ParsedEvent) -> ParsedEvent:
    event.sip_text = _extract_sip_text(event.raw_lines)
    if event.direction is None and event.preamble:
        direction, peer_ip, peer_port = _extract_direction(event.preamble)
        event.direction = direction
        event.peer_ip = peer_ip
        event.peer_port = peer_port
    return event


def parse_lines(lines: Iterator[str]) -> tuple[list[ParsedEvent], list[str]]:
    events: list[ParsedEvent] = []
    warnings: list[str] = []
    current: ParsedEvent | None = None

    for line in lines:
        stripped = line.rstrip("\n\r")
        if not stripped.strip():
            if current is not None:
                current.raw_lines.append("")
            continue

        if _is_syslog_header(stripped):
            if current is not None:
                events.append(_finalize_event(current))
            current = _parse_event_header(stripped)
            if current is None:
                warnings.append(f"Failed to parse syslog header: {stripped[:120]}")
        elif current is not None:
            current.raw_lines.append(stripped)
        else:
            warnings.append(f"Orphan line before first syslog header: {stripped[:120]}")

    if current is not None:
        events.append(_finalize_event(current))

    return events, warnings


def parse_file(file_obj: TextIO | BinaryIO) -> tuple[list[ParsedEvent], list[str]]:
    if hasattr(file_obj, "read"):
        content = file_obj.read()
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = content
        return parse_lines(iter(text.splitlines()))
    raise TypeError("file_obj must be readable")


def parse_sip_events(events: list[ParsedEvent]) -> list[ParsedEvent]:
    return [event for event in events if event.sip_text]
