from __future__ import annotations

import re
from dataclasses import dataclass, field

SIP_REQUEST_LINE_RE = re.compile(
    r"^(INVITE|ACK|BYE|CANCEL|OPTIONS|REGISTER|INFO|UPDATE|REFER|NOTIFY|SUBSCRIBE|MESSAGE|PRACK)\s+(.+?)\s+SIP/2\.0\s*$",
    re.IGNORECASE,
)
SIP_RESPONSE_LINE_RE = re.compile(
    r"^SIP/2\.0\s+(\d{3})\s+(.+?)\s*$",
    re.IGNORECASE,
)
HEADER_RE = re.compile(r"^([\w\-!.%*]+)\s*:\s*(.*)$")
FOLDED_HEADER_RE = re.compile(r"^\s+(.+)$")


@dataclass
class ParsedSipMessage:
    raw_text: str
    is_request: bool
    method: str | None = None
    request_uri: str | None = None
    status_code: int | None = None
    reason_phrase: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    call_id: str | None = None
    from_header: str | None = None
    to_header: str | None = None
    cseq: str | None = None
    via: str | None = None
    contact: str | None = None


def _normalize_header_key(key: str) -> str:
    return key.lower()


def _header_lookup(headers: dict[str, str], name: str) -> str | None:
    return headers.get(_normalize_header_key(name))


def parse_sip_message(text: str) -> ParsedSipMessage | None:
    text = text.strip()
    if not text:
        return None

    lines = text.splitlines()
    if not lines:
        return None

    first_line = lines[0].strip()
    parsed = ParsedSipMessage(raw_text=text, is_request=False)

    request_match = SIP_REQUEST_LINE_RE.match(first_line)
    if request_match:
        parsed.is_request = True
        parsed.method = request_match.group(1).upper()
        parsed.request_uri = request_match.group(2).strip()
    else:
        response_match = SIP_RESPONSE_LINE_RE.match(first_line)
        if not response_match:
            return None
        parsed.status_code = int(response_match.group(1))
        parsed.reason_phrase = response_match.group(2).strip()
        cseq_header = None
        for line in lines[1:]:
            header_match = HEADER_RE.match(line)
            if header_match and _normalize_header_key(header_match.group(1)) == "cseq":
                cseq_header = header_match.group(2).strip()
                break
        if cseq_header:
            parsed.method = cseq_header.split()[0].upper()

    header_lines = lines[1:]
    headers: dict[str, str] = {}
    current_key: str | None = None
    body_start: int | None = None

    for index, line in enumerate(header_lines):
        if line.strip() == "":
            body_start = index + 1
            break

        header_match = HEADER_RE.match(line)
        if header_match:
            current_key = _normalize_header_key(header_match.group(1))
            headers[current_key] = header_match.group(2).strip()
            continue

        folded_match = FOLDED_HEADER_RE.match(line)
        if folded_match and current_key:
            headers[current_key] = f"{headers[current_key]} {folded_match.group(1).strip()}"
            continue

        return None

    parsed.headers = headers
    if body_start is not None and body_start < len(header_lines):
        parsed.body = "\n".join(header_lines[body_start:]).strip() or None

    parsed.call_id = _header_lookup(headers, "Call-ID")
    parsed.from_header = _header_lookup(headers, "From")
    parsed.to_header = _header_lookup(headers, "To")
    parsed.cseq = _header_lookup(headers, "CSeq")
    parsed.via = _header_lookup(headers, "Via")
    parsed.contact = _header_lookup(headers, "Contact")
    return parsed


def extract_uri_host(uri: str | None) -> str | None:
    if not uri:
        return None
    uri = uri.strip()
    if "@" in uri:
        host_part = uri.split("@", 1)[1]
    else:
        host_part = uri
    host_part = host_part.split(";", 1)[0].strip()
    if host_part.startswith("sip:"):
        host_part = host_part[4:]
    if host_part.startswith("sips:"):
        host_part = host_part[5:]
    if ":" in host_part and not host_part.startswith("["):
        host_part = host_part.rsplit(":", 1)[0]
    return host_part.strip("<>") or None
