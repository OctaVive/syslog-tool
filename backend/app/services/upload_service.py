from __future__ import annotations

from collections import defaultdict
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Message, Session, Upload
from app.parsers.audiocodes_syslog import ParsedEvent, parse_file, parse_sip_events
from app.parsers.sip_message import ParsedSipMessage, extract_uri_host, parse_sip_message
from app.schemas.schemas import (
    FlowExportResponse,
    FlowParticipant,
    FlowResponse,
    FlowStep,
    MessageDetail,
    MessageSummary,
    SessionDetail,
    SessionSummary,
    UploadResponse,
)


async def process_upload(db: AsyncSession, filename: str, content: bytes) -> Upload:
    events, warnings = parse_file(BytesIO(content))
    sip_events = parse_sip_events(events)

    upload = Upload(
        filename=filename,
        parse_warnings=warnings[:100],
    )
    db.add(upload)
    await db.flush()

    grouped: dict[str, list[tuple[ParsedEvent, ParsedSipMessage]]] = defaultdict(list)
    for event in sip_events:
        if not event.sid or not event.sip_text:
            continue
        parsed = parse_sip_message(event.sip_text)
        if parsed is None:
            continue
        grouped[event.sid].append((event, parsed))

    total_messages = 0
    for sid, items in grouped.items():
        items.sort(key=lambda item: (item[0].timestamp, item[0].sequence))
        session = Session(
            upload_id=upload.id,
            sid=sid,
            message_count=len(items),
            first_timestamp=items[0][0].timestamp,
            last_timestamp=items[-1][0].timestamp,
        )

        methods: set[str] = set()
        for sort_order, (event, parsed) in enumerate(items):
            if parsed.method:
                methods.add(parsed.method)
            if parsed.call_id and not session.call_id:
                session.call_id = parsed.call_id
            if parsed.from_header and not session.from_header:
                session.from_header = parsed.from_header
            if parsed.to_header and not session.to_header:
                session.to_header = parsed.to_header

            db.add(
                Message(
                    session=session,
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

        session.methods = sorted(methods)
        db.add(session)
        total_messages += len(items)

    upload.session_count = len(grouped)
    upload.message_count = total_messages
    await db.commit()
    await db.refresh(upload)
    return upload


async def get_upload(db: AsyncSession, upload_id: str) -> Upload | None:
    return await db.get(Upload, upload_id)


def upload_to_response(upload: Upload) -> UploadResponse:
    return UploadResponse(
        id=upload.id,
        filename=upload.filename,
        uploaded_at=upload.uploaded_at,
        session_count=upload.session_count,
        message_count=upload.message_count,
        parse_warnings=upload.parse_warnings or [],
    )


async def list_sessions(
    db: AsyncSession,
    upload_id: str,
    sid: str | None = None,
    call_id: str | None = None,
    from_header: str | None = None,
    to_header: str | None = None,
    method: str | None = None,
) -> list[SessionSummary]:
    query = select(Session).where(Session.upload_id == upload_id).order_by(Session.first_timestamp)

    if sid:
        query = query.where(Session.sid.ilike(f"%{sid}%"))
    if call_id:
        query = query.where(Session.call_id.ilike(f"%{call_id}%"))
    if from_header:
        query = query.where(Session.from_header.ilike(f"%{from_header}%"))
    if to_header:
        query = query.where(Session.to_header.ilike(f"%{to_header}%"))
    result = await db.execute(query)
    sessions = result.scalars().all()

    if method:
        method_upper = method.upper()
        sessions = [
            session
            for session in sessions
            if method_upper in (session.methods or [])
        ]

    return [
        SessionSummary(
            id=session.id,
            upload_id=session.upload_id,
            sid=session.sid,
            call_id=session.call_id,
            from_header=session.from_header,
            to_header=session.to_header,
            first_timestamp=session.first_timestamp,
            last_timestamp=session.last_timestamp,
            message_count=session.message_count,
            methods=session.methods or [],
        )
        for session in sessions
    ]


def _summary_from_message(message: Message) -> MessageSummary:
    if message.method and message.status_code is None:
        label = message.method
    elif message.status_code is not None:
        label = str(message.status_code)
    else:
        label = "SIP"
    return MessageSummary(
        id=message.id,
        sequence=message.sequence,
        timestamp=message.timestamp,
        device_ip=message.device_ip,
        direction=message.direction,
        peer_ip=message.peer_ip,
        peer_port=message.peer_port,
        method=message.method,
        status_code=message.status_code,
        call_id=message.call_id,
        from_header=message.from_header,
        to_header=message.to_header,
        sort_order=message.sort_order,
        label=label,
    )


async def get_session_detail(db: AsyncSession, session_id: str) -> SessionDetail | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.messages))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    messages = sorted(session.messages, key=lambda message: message.sort_order)
    return SessionDetail(
        id=session.id,
        upload_id=session.upload_id,
        sid=session.sid,
        call_id=session.call_id,
        from_header=session.from_header,
        to_header=session.to_header,
        first_timestamp=session.first_timestamp,
        last_timestamp=session.last_timestamp,
        message_count=session.message_count,
        methods=session.methods or [],
        messages=[_summary_from_message(message) for message in messages],
    )


async def get_message_detail(db: AsyncSession, message_id: str) -> MessageDetail | None:
    message = await db.get(Message, message_id)
    if message is None:
        return None
    return MessageDetail(
        id=message.id,
        session_id=message.session_id,
        sequence=message.sequence,
        timestamp=message.timestamp,
        device_ip=message.device_ip,
        severity=message.severity,
        direction=message.direction,
        peer_ip=message.peer_ip,
        peer_port=message.peer_port,
        raw_text=message.raw_text,
        method=message.method,
        status_code=message.status_code,
        call_id=message.call_id,
        from_header=message.from_header,
        to_header=message.to_header,
        cseq=message.cseq,
        via=message.via,
        headers=message.headers or {},
        body=message.body,
        sort_order=message.sort_order,
    )


def _resolve_participants(messages: list[Message]) -> dict[str, str]:
    participants: dict[str, str] = {}

    for message in messages:
        sbc_id = f"sbc:{message.device_ip}"
        participants.setdefault(sbc_id, f"SBC ({message.device_ip})")

        if message.peer_ip:
            peer_id = f"peer:{message.peer_ip}:{message.peer_port or 0}"
            label = message.peer_ip
            if message.peer_port:
                label = f"{message.peer_ip}:{message.peer_port}"
            participants.setdefault(peer_id, label)

        from_host = extract_uri_host(message.from_header)
        if from_host:
            participants.setdefault(f"host:{from_host}", from_host)

        to_host = extract_uri_host(message.to_header)
        if to_host:
            participants.setdefault(f"host:{to_host}", to_host)

    return participants


def _step_endpoints(message: Message, participants: dict[str, str]) -> tuple[str, str]:
    sbc_id = f"sbc:{message.device_ip}"

    if message.direction == "outgoing" and message.peer_ip:
        peer_id = f"peer:{message.peer_ip}:{message.peer_port or 0}"
        if message.status_code is not None:
            return peer_id if peer_id in participants else sbc_id, sbc_id
        return sbc_id, peer_id if peer_id in participants else sbc_id

    if message.direction == "incoming" and message.peer_ip:
        peer_id = f"peer:{message.peer_ip}:{message.peer_port or 0}"
        if message.status_code is not None:
            return sbc_id, peer_id if peer_id in participants else sbc_id
        return peer_id if peer_id in participants else sbc_id, sbc_id

    from_host = extract_uri_host(message.from_header)
    to_host = extract_uri_host(message.to_header)
    from_id = f"host:{from_host}" if from_host and f"host:{from_host}" in participants else sbc_id
    to_id = f"host:{to_host}" if to_host and f"host:{to_host}" in participants else sbc_id

    if message.status_code is not None:
        return to_id, from_id
    return from_id, to_id


def build_flow(session: Session, messages: list[Message]) -> FlowResponse:
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
        session_id=session.id,
        sid=session.sid,
        participants=participants,
        steps=steps,
    )


async def get_session_flow(db: AsyncSession, session_id: str) -> FlowResponse | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.messages))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    messages = sorted(session.messages, key=lambda message: message.sort_order)
    return build_flow(session, messages)


def build_flow_export(flow: FlowResponse, session: Session, messages: list[Message]) -> FlowExportResponse:
    participant_labels = {participant.id: participant.label for participant in flow.participants}
    lines = [
        f"SIP Call Flow - SID: {session.sid}",
        f"Call-ID: {session.call_id or 'n/a'}",
        f"Messages: {session.message_count}",
        "",
    ]

    message_map = {message.id: message for message in messages}
    for step in flow.steps:
        from_label = participant_labels.get(step.from_participant, step.from_participant)
        to_label = participant_labels.get(step.to_participant, step.to_participant)
        arrow = "->" if step.is_request else "<-"
        lines.append(f"[{step.timestamp}] {from_label} {arrow} {to_label} : {step.label}")
        message = message_map.get(step.message_id)
        if message:
            lines.append(message.raw_text)
            lines.append("")

    return FlowExportResponse(session_id=session.id, sid=session.sid, text="\n".join(lines))


async def get_session_flow_export(db: AsyncSession, session_id: str) -> FlowExportResponse | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.messages))
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    messages = sorted(session.messages, key=lambda message: message.sort_order)
    flow = build_flow(session, messages)
    return build_flow_export(flow, session, messages)
