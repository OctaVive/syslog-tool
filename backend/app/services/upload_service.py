from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO

from app.parsers.audiocodes_syslog import ParsedEvent, parse_file, parse_sip_events
from app.parsers.sip_message import ParsedSipMessage, extract_uri_host, parse_sip_message
from app.schemas.schemas import (
    AnalysisResponse,
    AnalysisSession,
    FlowParticipant,
    FlowResponse,
    FlowStep,
    MessageDetail,
)


def parse_upload(filename: str, content: bytes) -> AnalysisResponse:
    events, warnings = parse_file(BytesIO(content))
    sip_events = parse_sip_events(events)
    upload_id = str(uuid.uuid4())

    grouped: dict[str, list[tuple[ParsedEvent, ParsedSipMessage]]] = defaultdict(list)
    for event in sip_events:
        if not event.sip_text:
            continue
        parsed = parse_sip_message(event.sip_text)
        if parsed is None:
            continue
        session_key = event.sid or (f"call:{parsed.call_id}" if parsed.call_id else None)
        if not session_key:
            continue
        grouped[session_key].append((event, parsed))

    sessions: list[AnalysisSession] = []
    total_messages = 0
    for sid, items in grouped.items():
        items.sort(key=lambda item: (item[0].timestamp, item[0].sequence))
        session_id = str(uuid.uuid4())
        messages: list[MessageDetail] = []
        methods: set[str] = set()
        call_id: str | None = None
        from_header: str | None = None
        to_header: str | None = None

        for sort_order, (event, parsed) in enumerate(items):
            if parsed.method:
                methods.add(parsed.method)
            if parsed.call_id and not call_id:
                call_id = parsed.call_id
            if parsed.from_header and not from_header:
                from_header = parsed.from_header
            if parsed.to_header and not to_header:
                to_header = parsed.to_header
            messages.append(
                MessageDetail(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    sequence=event.sequence,
                    timestamp=event.timestamp,
                    device_ip=event.device_ip,
                    severity=event.severity,
                    direction=event.direction,
                    peer_ip=event.peer_ip,
                    peer_port=event.peer_port,
                    raw_text=parsed.raw_text,
                    method=parsed.method,
                    status_code=parsed.status_code,
                    call_id=parsed.call_id,
                    from_header=parsed.from_header,
                    to_header=parsed.to_header,
                    cseq=parsed.cseq,
                    via=parsed.via,
                    headers=parsed.headers,
                    body=parsed.body,
                    sort_order=sort_order,
                )
            )

        sessions.append(
            AnalysisSession(
                id=session_id,
                upload_id=upload_id,
                sid=sid,
                call_id=call_id,
                from_header=from_header,
                to_header=to_header,
                first_timestamp=items[0][0].timestamp,
                last_timestamp=items[-1][0].timestamp,
                message_count=len(messages),
                methods=sorted(methods),
                messages=messages,
                flow=build_flow(session_id, sid, messages),
            )
        )
        total_messages += len(messages)

    sessions.sort(key=lambda session: session.first_timestamp or "")
    return AnalysisResponse(
        id=upload_id,
        filename=filename,
        uploaded_at=datetime.now(timezone.utc),
        session_count=len(sessions),
        message_count=total_messages,
        parse_warnings=warnings[:100],
        sessions=sessions,
    )


def _host_id(host: str | None) -> str | None:
    if not host:
        return None
    return f"host:{host}"


def _resolve_participants(messages: list[MessageDetail]) -> dict[str, str]:
    participants: dict[str, str] = {}
    for message in messages:
        for host in (
            extract_uri_host(message.from_header),
            extract_uri_host(message.to_header),
        ):
            if host:
                participants.setdefault(f"host:{host}", host)
    return participants


def _other_host(host_id: str, participants: dict[str, str]) -> str | None:
    for participant_id in participants:
        if participant_id != host_id:
            return participant_id
    return None


def _step_endpoints(message: MessageDetail, participants: dict[str, str]) -> tuple[str, str]:
    from_id = _host_id(extract_uri_host(message.from_header))
    to_id = _host_id(extract_uri_host(message.to_header))
    fallback = next(iter(participants), "unknown")
    from_id = from_id or fallback
    to_id = to_id or fallback

    if from_id == to_id:
        other = _other_host(from_id, participants)
        if other is None:
            return from_id, to_id
        if message.status_code is not None:
            return other, from_id
        return from_id, other

    if message.status_code is not None:
        return to_id, from_id
    return from_id, to_id


def build_flow(session_id: str, sid: str, messages: list[MessageDetail]) -> FlowResponse:
    participants_map = _resolve_participants(messages)
    participants = [
        FlowParticipant(id=participant_id, label=label)
        for participant_id, label in participants_map.items()
    ]

    steps: list[FlowStep] = []
    for message in messages:
        from_id, to_id = _step_endpoints(message, participants_map)
        if message.method and message.status_code is None:
            label = message.method
            is_request = True
        elif message.status_code is not None:
            label = f"{message.status_code}"
            is_request = False
        else:
            label = "SIP"
            is_request = message.method is not None

        steps.append(
            FlowStep(
                message_id=message.id,
                from_participant=from_id,
                to_participant=to_id,
                label=label,
                is_request=is_request,
                timestamp=message.timestamp,
                sort_order=message.sort_order,
            )
        )

    return FlowResponse(
        session_id=session_id,
        sid=sid,
        participants=participants,
        steps=steps,
    )
