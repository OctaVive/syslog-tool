import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getSessions, getUpload } from "@/api/client";

const SIP_METHODS = ["INVITE", "OPTIONS", "REGISTER", "BYE", "ACK", "CANCEL", "NOTIFY", "SUBSCRIBE"];

export default function SessionsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const uploadId = searchParams.get("uploadId") || sessionStorage.getItem("lastUploadId") || "";

  const [sid, setSid] = useState(searchParams.get("sid") || "");
  const [callId, setCallId] = useState(searchParams.get("call_id") || "");
  const [from, setFrom] = useState(searchParams.get("from") || "");
  const [to, setTo] = useState(searchParams.get("to") || "");
  const [method, setMethod] = useState(searchParams.get("method") || "");

  const filters = useMemo(
    () => ({
      sid: sid || undefined,
      call_id: callId || undefined,
      from: from || undefined,
      to: to || undefined,
      method: method || undefined,
    }),
    [sid, callId, from, to, method],
  );

  const uploadQuery = useQuery({
    queryKey: ["upload", uploadId],
    queryFn: () => getUpload(uploadId),
    enabled: Boolean(uploadId),
  });

  const sessionsQuery = useQuery({
    queryKey: ["sessions", uploadId, filters],
    queryFn: () => getSessions(uploadId, filters),
    enabled: Boolean(uploadId),
  });

  const applyFilters = () => {
    const params = new URLSearchParams({ uploadId });
    if (sid) params.set("sid", sid);
    if (callId) params.set("call_id", callId);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    if (method) params.set("method", method);
    setSearchParams(params);
  };

  if (!uploadId) {
    return (
      <div className="app-card p-6">
        <p>Geen upload geselecteerd. Upload eerst een syslog bestand.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="app-page-title">SIP sessies</h1>
        <p className="app-page-subtitle">
          {uploadQuery.data
            ? `${uploadQuery.data.filename} — ${uploadQuery.data.session_count} sessies`
            : "Laden..."}
        </p>
      </div>

      <div className="app-card p-4 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <input className="app-input" placeholder="SID" value={sid} onChange={(e) => setSid(e.target.value)} />
        <input className="app-input" placeholder="Call-ID" value={callId} onChange={(e) => setCallId(e.target.value)} />
        <input className="app-input" placeholder="From" value={from} onChange={(e) => setFrom(e.target.value)} />
        <input className="app-input" placeholder="To" value={to} onChange={(e) => setTo(e.target.value)} />
        <select className="app-input" value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="">Method (alle)</option>
          {SIP_METHODS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button className="app-btn-primary" onClick={applyFilters}>
          Filter
        </button>
      </div>

      <div className="app-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-neutral-950 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">SID</th>
                <th className="px-4 py-3 font-medium">Call-ID</th>
                <th className="px-4 py-3 font-medium">From</th>
                <th className="px-4 py-3 font-medium">To</th>
                <th className="px-4 py-3 font-medium">Tijd</th>
                <th className="px-4 py-3 font-medium">Berichten</th>
                <th className="px-4 py-3 font-medium">Methods</th>
              </tr>
            </thead>
            <tbody>
              {sessionsQuery.isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-gray-500">
                    Laden...
                  </td>
                </tr>
              )}
              {sessionsQuery.data?.map((session) => (
                <tr
                  key={session.id}
                  className="border-t border-gray-100 dark:border-neutral-800 hover:bg-gray-50 dark:hover:bg-neutral-900/50 cursor-pointer"
                  onClick={() => navigate(`/flow/${session.id}?uploadId=${uploadId}`)}
                >
                  <td className="px-4 py-3 font-mono text-xs">{session.sid}</td>
                  <td className="px-4 py-3 font-mono text-xs max-w-xs truncate">{session.call_id || "—"}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{session.from_header || "—"}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{session.to_header || "—"}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {session.first_timestamp}
                    {session.last_timestamp && session.last_timestamp !== session.first_timestamp
                      ? ` – ${session.last_timestamp}`
                      : ""}
                  </td>
                  <td className="px-4 py-3">{session.message_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {session.methods.map((item) => (
                        <span
                          key={item}
                          className="px-2 py-0.5 rounded-full bg-brand/10 text-brand text-xs font-medium"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {sessionsQuery.data?.length === 0 && !sessionsQuery.isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-gray-500">
                    Geen sessies gevonden voor deze filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
