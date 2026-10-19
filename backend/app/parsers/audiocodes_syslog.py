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

_DATE = r"(?:[A-Za-z]{3}\s+\d{1,2}|\d{4}-\d{2}-\d{2}|\d{2}[-/]\d{2}[-/]\d{2,4})"
_TIME = r"\d{2}:\d{2}:\d{2}(?:\.\d+)?"
_IPV4 = r"\d{1,3}(?:\.\d{1,3}){3}"

SYSLOG_HEADER_RE = re.compile(
    rf"^(?:(?P<date>{_DATE})\s+)?"
    rf"(?P<time>{_TIME})\s+"
    rf"(?:(?P<device>{_IPV4})\s+)?"
    rf"(?P<severity>[\w.]+)\s+"
    rf"\[S=(?P<sequence>\d+)\]\s*"
    rf"(?P<ids>(?:\[(?:SID|BID)[=:][^\]]+\]\s*)*)"
    rf"(?P<preamble>.*)$",
    re.IGNORECASE,
)
ID_TOKEN_RE = re.compile(r"\[(SID|BID)[=:]([^\]]+)\]", re.IGNORECASE)
TIME_TRAILER_RE = re.compile(
    r"^\[Time:(?P<stamp>[^\]]+)\](?:\s+\[(?P<seq>\d+)\])?\s*$",
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
    part: int = 0


def _is_syslog_header(line: str) -> bool:
    return bool(SYSLOG_HEADER_RE.match(line.strip()))


def _extract_direction(text: str) -> tuple[str | None, str | None, int | None]:
    match = DIRECTION_RE.search(text)
    if not match:
        return None, None, None
    direction = match.group(1).lower()
    return direction, match.group(2), int(match.group(3))


def _ids_from_header(match: re.Match[str]) -> tuple[str | None, str | None]:
    sid: str | None = None
    bid: str | None = None
    for kind, value in ID_TOKEN_RE.findall(match.group("ids") or ""):
        if kind.upper() == "SID":
            sid = value
        elif kind.upper() == "BID":
            bid = value
    return sid, bid


def _sip_payload(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or TIME_TRAILER_RE.match(stripped):
        return None
    if SIP_REQUEST_RE.match(stripped) or SIP_RESPONSE_RE.match(stripped):
        return stripped
    header = SYSLOG_HEADER_RE.match(stripped)
    if not header:
        return None
    preamble = header.group("preamble").strip()
    if SIP_REQUEST_RE.match(preamble) or SIP_RESPONSE_RE.match(preamble):
        return preamble
    return None


def _extract_sip_text(lines: list[str]) -> str | None:
    collected: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if TIME_TRAILER_RE.match(stripped):
            break
        if not started:
            payload = _sip_payload(line)
            if payload is None:
                continue
            collected.append(payload)
            started = True
            continue
        collected.append(line.rstrip())
    text = "\n".join(collected).strip()
    return text or None


def _apply_direction(event: ParsedEvent) -> None:
    for line in event.raw_lines:
        direction, peer_ip, peer_port = _extract_direction(line)
        if direction is None:
            continue
        event.direction = direction
        event.peer_ip = peer_ip
        event.peer_port = peer_port
        return


def _parse_event_header(line: str) -> ParsedEvent | None:
    match = SYSLOG_HEADER_RE.match(line.strip())
    if not match:
        return None
    date = match.group("date")
    timestamp = f"{date} {match.group('time')}" if date else match.group("time")
    sid, bid = _ids_from_header(match)
    preamble = match.group("preamble").strip()
    return ParsedEvent(
        timestamp=timestamp,
        device_ip=match.group("device") or "",
        severity=match.group("severity"),
        sequence=int(match.group("sequence")),
        sid=sid,
        bid=bid,
        preamble=preamble,
        raw_lines=[line.rstrip("\n\r")],
    )


def _header_already_closed(event: ParsedEvent) -> bool:
    """A header that already carries [Time:] and no SIP marker is a finished record.

    AudioCodes sometimes prints the SIP payload on the following lines of the same
    record, and that header also contains [Time:]. Those lines stay with the record
    because the direction marker or the request line is on the header. A later SIP
    block after a finished non-SIP record is a separate message whose header was
    not included in the export.
    """
    if not event.raw_lines:
        return False
    header = event.raw_lines[0]
    if not re.search(r"\[Time:", header, re.IGNORECASE):
        return False
    if _extract_direction(header)[0] is not None:
        return False
    if _sip_payload(header) is not None:
        return False
    return True


def _trailer_timestamp(lines: list[str]) -> tuple[str, int]:
    for line in lines:
        match = TIME_TRAILER_RE.match(line.strip())
        if not match:
            continue
        timestamp = match.group("stamp").strip().replace("@", " ")
        sequence = int(match.group("seq")) if match.group("seq") else 0
        return timestamp, sequence
    return "", 0


def _event_from_orphan(lines: list[str]) -> ParsedEvent | None:
    if _extract_sip_text(lines) is None:
        return None
    timestamp, sequence = _trailer_timestamp(lines)
    event = ParsedEvent(
        timestamp=timestamp,
        device_ip="",
        severity="",
        sequence=sequence,
        sid=None,
        bid=None,
        preamble="",
        raw_lines=list(lines),
    )
    return _finalize_event(event)


def _sip_blocks(
    lines: list[str],
) -> list[tuple[str | None, str | None, int | None, str]]:
    """Split one syslog record into the SIP messages it contains.

    AudioCodes writes a direction marker before each message and sometimes packs
    several messages into one record. A marker with no following SIP message is
    ignored, so a trailing marker does not duplicate the message logged next.
    """
    blocks: list[tuple[str | None, str | None, int | None, str]] = []
    pending: tuple[str | None, str | None, int | None] = (None, None, None)
    current: list[str] | None = None
    current_direction: tuple[str | None, str | None, int | None] = pending

    def close() -> None:
        nonlocal current
        if current is None:
            return
        text = "\n".join(current).strip()
        if text:
            blocks.append((*current_direction, text))
        current = None

    for line in lines:
        stripped = line.strip()
        if TIME_TRAILER_RE.match(stripped):
            close()
            break
        direction, peer_ip, peer_port = _extract_direction(line)
        if direction is not None:
            close()
            pending = (direction, peer_ip, peer_port)
            continue
        payload = _sip_payload(line)
        if payload is not None and (current is None or payload == stripped):
            close()
            current = [payload]
            current_direction = pending
            pending = (None, None, None)
            continue
        if current is not None:
            current.append(line.rstrip())
    close()
    return blocks


def _expand_event(event: ParsedEvent) -> list[ParsedEvent]:
    blocks = _sip_blocks(event.raw_lines)
    if not blocks:
        event.sip_text = None
        return [event]
    expanded: list[ParsedEvent] = []
    for index, (direction, peer_ip, peer_port, text) in enumerate(blocks):
        if index == 0:
            event.part = 0
            event.direction = direction
            event.peer_ip = peer_ip
            event.peer_port = peer_port
            event.sip_text = text
            expanded.append(event)
            continue
        expanded.append(
            ParsedEvent(
                timestamp=event.timestamp,
                device_ip=event.device_ip,
                severity=event.severity,
                sequence=event.sequence,
                sid=event.sid,
                bid=event.bid,
                preamble=event.preamble,
                direction=direction,
                peer_ip=peer_ip,
                peer_port=peer_port,
                sip_text=text,
                part=index,
            )
        )
    return expanded


def _finalize_event(event: ParsedEvent) -> ParsedEvent:
    return _expand_event(event)[0]


def _collapse_double_spacing(lines: list[str]) -> list[str]:
    """Drop blank lines inserted after every content line in web exports.

    A normal syslog keeps SIP headers contiguous and uses a single blank line
    as the header/body separator. Those files are left unchanged. A web export
    alternates content and blank lines, so a gap larger than one blank is kept
    as the real separator.
    """
    content_indexes = [index for index, line in enumerate(lines) if line.strip()]
    if len(content_indexes) < 2:
        return [line.rstrip() for line in lines]

    single_blank_gaps = 0
    other_gaps = 0
    for left, right in zip(content_indexes, content_indexes[1:]):
        gap = right - left - 1
        if gap == 1 and not lines[left + 1].strip():
            single_blank_gaps += 1
        elif gap > 0:
            other_gaps += 1

    if single_blank_gaps <= other_gaps or single_blank_gaps <= len(content_indexes) * 0.5:
        return [line.rstrip() for line in lines]

    collapsed: list[str] = []
    previous: int | None = None
    for index in content_indexes:
        if previous is not None and index - previous > 2:
            collapsed.append("")
        collapsed.append(lines[index].rstrip())
        previous = index
    return collapsed


def _normalize_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return _collapse_double_spacing(lines)


def parse_lines(lines: Iterator[str]) -> tuple[list[ParsedEvent], list[str]]:
    events: list[ParsedEvent] = []
    warnings: list[str] = []
    current: ParsedEvent | None = None
    orphan: list[str] = []

    def flush_orphan() -> None:
        if not any(line.strip() for line in orphan):
            orphan.clear()
            return
        event = _event_from_orphan(orphan)
        if event is not None:
            events.extend(_expand_event(event))
        else:
            for line in orphan:
                stripped = line.strip()
                if stripped and not TIME_TRAILER_RE.match(stripped):
                    warnings.append(f"Orphan line outside syslog record: {stripped[:120]}")
        orphan.clear()

    def close_current() -> None:
        nonlocal current
        if current is None:
            return
        events.extend(_expand_event(current))
        current = None

    for line in lines:
        stripped = line.rstrip("\n\r")
        if not stripped.strip():
            if current is not None:
                current.raw_lines.append("")
            elif orphan:
                orphan.append("")
            continue

        if TIME_TRAILER_RE.match(stripped.strip()):
            if current is not None:
                current.raw_lines.append(stripped)
                close_current()
            elif orphan:
                orphan.append(stripped)
                flush_orphan()
            else:
                warnings.append(f"Orphan line outside syslog record: {stripped.strip()[:120]}")
            continue

        if _is_syslog_header(stripped):
            flush_orphan()
            close_current()
            current = _parse_event_header(stripped)
            if current is None:
                warnings.append(f"Failed to parse syslog header: {stripped[:120]}")
            continue

        if (
            current is not None
            and _sip_payload(stripped) == stripped.strip()
            and _header_already_closed(current)
            and _extract_sip_text(current.raw_lines) is None
        ):
            close_current()
            orphan.append(stripped)
            continue

        if current is not None:
            current.raw_lines.append(stripped)
        else:
            orphan.append(stripped)

    flush_orphan()
    close_current()
    return events, warnings


def parse_file(file_obj: TextIO | BinaryIO) -> tuple[list[ParsedEvent], list[str]]:
    if hasattr(file_obj, "read"):
        content = file_obj.read()
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = content
        return parse_lines(iter(_normalize_lines(text)))
    raise TypeError("file_obj must be readable")


def parse_sip_events(events: list[ParsedEvent]) -> list[ParsedEvent]:
    return [event for event in events if event.sip_text]
