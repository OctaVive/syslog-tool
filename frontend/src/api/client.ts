export interface UploadResponse {
  id: string;
  filename: string;
  uploaded_at: string;
  session_count: number;
  message_count: number;
  parse_warnings: string[];
}

export interface SessionSummary {
  id: string;
  upload_id: string;
  sid: string;
  call_id: string | null;
  from_header: string | null;
  to_header: string | null;
  first_timestamp: string | null;
  last_timestamp: string | null;
  message_count: number;
  methods: string[];
}

export interface MessageSummary {
  id: string;
  sequence: number;
  timestamp: string;
  device_ip: string;
  direction: string | null;
  peer_ip: string | null;
  peer_port: number | null;
  method: string | null;
  status_code: number | null;
  call_id: string | null;
  from_header: string | null;
  to_header: string | null;
  sort_order: number;
  label: string;
}

export interface MessageDetail {
  id: string;
  session_id: string;
  sequence: number;
  timestamp: string;
  device_ip: string;
  severity: string;
  direction: string | null;
  peer_ip: string | null;
  peer_port: number | null;
  raw_text: string;
  method: string | null;
  status_code: number | null;
  call_id: string | null;
  from_header: string | null;
  to_header: string | null;
  cseq: string | null;
  via: string | null;
  headers: Record<string, string>;
  body: string | null;
  sort_order: number;
}

export interface FlowParticipant {
  id: string;
  label: string;
}

export interface FlowStep {
  message_id: string;
  from_participant: string;
  to_participant: string;
  label: string;
  is_request: boolean;
  timestamp: string;
  sort_order: number;
}

export interface FlowResponse {
  session_id: string;
  sid: string;
  participants: FlowParticipant[];
  steps: FlowStep[];
}

export interface FlowExportResponse {
  session_id: string;
  sid: string;
  text: string;
}

export interface AnalysisSession extends SessionSummary {
  messages: MessageDetail[];
  flow: FlowResponse;
}

export interface AnalysisResponse extends UploadResponse {
  sessions: AnalysisSession[];
}

const STORAGE_KEY = "syslog-analysis";

export function saveAnalysis(analysis: AnalysisResponse): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(analysis));
}

export function loadAnalysis(): AnalysisResponse | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AnalysisResponse;
  } catch {
    return null;
  }
}

export function clearAnalysis(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function filterSessions(
  sessions: AnalysisSession[],
  filters: {
    sid?: string;
    call_id?: string;
    from?: string;
    to?: string;
    method?: string;
  },
): AnalysisSession[] {
  const contains = (value: string | null, query: string | undefined) => {
    if (!query) return true;
    return (value || "").toLowerCase().includes(query.toLowerCase());
  };
  return sessions.filter((session) => {
    if (!contains(session.sid, filters.sid)) return false;
    if (!contains(session.call_id, filters.call_id)) return false;
    if (!contains(session.from_header, filters.from)) return false;
    if (!contains(session.to_header, filters.to)) return false;
    if (filters.method && !session.methods.includes(filters.method.toUpperCase())) return false;
    return true;
  });
}

export function buildFlowExport(session: AnalysisSession): string {
  const labels = Object.fromEntries(session.flow.participants.map((participant) => [participant.id, participant.label]));
  const messages = Object.fromEntries(session.messages.map((message) => [message.id, message]));
  const lines = [
    `SIP Call Flow - SID: ${session.sid}`,
    `Call-ID: ${session.call_id || "n/a"}`,
    `Messages: ${session.message_count}`,
    "",
  ];
  for (const step of session.flow.steps) {
    const fromLabel = labels[step.from_participant] ?? step.from_participant;
    const toLabel = labels[step.to_participant] ?? step.to_participant;
    const arrow = step.is_request ? "->" : "<-";
    lines.push(`[${step.timestamp}] ${fromLabel} ${arrow} ${toLabel} : ${step.label}`);
    const message = messages[step.message_id];
    if (message) {
      lines.push(message.raw_text);
      lines.push("");
    }
  }
  return lines.join("\n");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function uploadSyslog(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const analysis = await request<AnalysisResponse>("/api/uploads", { method: "POST", body: formData });
  saveAnalysis(analysis);
  return analysis;
}
