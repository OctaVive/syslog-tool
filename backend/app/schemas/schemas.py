from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    session_count: int
    message_count: int
    parse_warnings: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    id: str
    upload_id: str
    sid: str
    call_id: str | None
    from_header: str | None
    to_header: str | None
    first_timestamp: str | None
    last_timestamp: str | None
    message_count: int
    methods: list[str]


class MessageSummary(BaseModel):
    id: str
    sequence: int
    timestamp: str
    device_ip: str
    direction: str | None
    peer_ip: str | None
    peer_port: int | None
    method: str | None
    status_code: int | None
    call_id: str | None
    from_header: str | None
    to_header: str | None
    sort_order: int
    label: str


class MessageDetail(BaseModel):
    id: str
    session_id: str
    sequence: int
    timestamp: str
    device_ip: str
    severity: str
    direction: str | None
    peer_ip: str | None
    peer_port: int | None
    raw_text: str
    method: str | None
    status_code: int | None
    reason_phrase: str | None
    call_id: str | None
    from_header: str | None
    to_header: str | None
    cseq: str | None
    via: str | None
    headers: dict[str, str]
    body: str | None
    sort_order: int


class SessionDetail(BaseModel):
    id: str
    upload_id: str
    sid: str
    call_id: str | None
    from_header: str | None
    to_header: str | None
    first_timestamp: str | None
    last_timestamp: str | None
    message_count: int
    methods: list[str]
    messages: list[MessageSummary]


class FlowParticipant(BaseModel):
    id: str
    label: str


class FlowStep(BaseModel):
    message_id: str
    from_participant: str
    to_participant: str
    label: str
    is_request: bool
    timestamp: str
    sort_order: int


class FlowResponse(BaseModel):
    session_id: str
    sid: str
    participants: list[FlowParticipant]
    steps: list[FlowStep]


class FlowExportResponse(BaseModel):
    session_id: str
    sid: str
    text: str


class AnalysisSession(SessionSummary):
    messages: list[MessageDetail]
    flow: FlowResponse


class AnalysisResponse(UploadResponse):
    sessions: list[AnalysisSession]
