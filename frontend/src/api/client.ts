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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function uploadSyslog(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadResponse>("/api/uploads", { method: "POST", body: formData });
}

export async function getUpload(uploadId: string): Promise<UploadResponse> {
  return request<UploadResponse>(`/api/uploads/${uploadId}`);
}

export async function getSessions(
  uploadId: string,
  filters: {
    sid?: string;
    call_id?: string;
    from?: string;
    to?: string;
    method?: string;
  } = {},
): Promise<SessionSummary[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return request<SessionSummary[]>(`/api/uploads/${uploadId}/sessions${query ? `?${query}` : ""}`);
}

export async function getMessage(messageId: string): Promise<MessageDetail> {
  return request<MessageDetail>(`/api/messages/${messageId}`);
}

export async function getSessionFlow(sessionId: string): Promise<FlowResponse> {
  return request<FlowResponse>(`/api/sessions/${sessionId}/flow`);
}

export async function exportSessionFlow(sessionId: string): Promise<FlowExportResponse> {
  return request<FlowExportResponse>(`/api/sessions/${sessionId}/flow/export`);
}
