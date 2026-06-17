import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { exportSessionFlow, getMessage, getSessionFlow } from "@/api/client";
import MessageDetailPanel from "@/components/MessageDetailPanel";
import SipLadderDiagram from "@/components/SipLadderDiagram";

export default function FlowPage() {
  const { sessionId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const uploadId = searchParams.get("uploadId") || "";
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  const flowQuery = useQuery({
    queryKey: ["flow", sessionId],
    queryFn: () => getSessionFlow(sessionId),
    enabled: Boolean(sessionId),
  });

  useEffect(() => {
    setSelectedMessageId(null);
  }, [sessionId]);

  useEffect(() => {
    if (flowQuery.data?.steps.length && !selectedMessageId) {
      setSelectedMessageId(flowQuery.data.steps[0].message_id);
    }
  }, [flowQuery.data, selectedMessageId]);

  const messageQuery = useQuery({
    queryKey: ["message", selectedMessageId],
    queryFn: () => getMessage(selectedMessageId!),
    enabled: Boolean(selectedMessageId),
  });

  const handleExport = async () => {
    const exported = await exportSessionFlow(sessionId);
    const blob = new Blob([exported.text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `sip-flow-${exported.sid.replace(/[:/\\]/g, "_")}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (flowQuery.isLoading) {
    return <div className="app-card p-6">Call flow laden...</div>;
  }

  if (flowQuery.isError || !flowQuery.data) {
    return <div className="app-card p-6">Kon call flow niet laden.</div>;
  }

  const flow = flowQuery.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <Link
            to={`/sessions?uploadId=${uploadId}`}
            className="inline-flex items-center gap-1 text-sm text-brand hover:underline mb-2"
          >
            <ArrowLeft size={16} />
            Terug naar sessies
          </Link>
          <h1 className="app-page-title">SIP Call Flow</h1>
          <p className="app-page-subtitle">
            SID {flow.sid} · {flow.steps.length} berichten
          </p>
        </div>
        <button className="app-btn-secondary inline-flex items-center gap-2" onClick={handleExport}>
          <Download size={16} />
          Export TXT
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 min-h-[640px]">
        <div className="xl:col-span-2 min-h-[480px]">
          <SipLadderDiagram
            flow={flow}
            selectedMessageId={selectedMessageId}
            onSelect={setSelectedMessageId}
          />
        </div>
        <div className="min-h-[480px]">
          <MessageDetailPanel message={messageQuery.data ?? null} loading={messageQuery.isLoading} />
        </div>
      </div>
    </div>
  );
}
