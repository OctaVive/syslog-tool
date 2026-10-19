import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Download } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { buildFlowExport, loadAnalysis } from "@/api/client";
import MessageDetailPanel from "@/components/MessageDetailPanel";
import SipLadderDiagram from "@/components/SipLadderDiagram";
import { useLanguage } from "@/context/LanguageContext";

export default function FlowPage() {
  const { sessionId = "" } = useParams();
  const { t } = useLanguage();
  const [searchParams] = useSearchParams();
  const uploadId = searchParams.get("uploadId") || loadAnalysis()?.id || "";
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  const session = useMemo(() => {
    const analysis = loadAnalysis();
    if (!analysis || (uploadId && analysis.id !== uploadId)) return null;
    return analysis.sessions.find((item) => item.id === sessionId) ?? null;
  }, [sessionId, uploadId]);

  useEffect(() => {
    setSelectedMessageId(session?.flow.steps[0]?.message_id ?? null);
  }, [session]);

  const message = session?.messages.find((item) => item.id === selectedMessageId) ?? null;
  const rowRef = useRef<HTMLDivElement>(null);
  const [panelWidth, setPanelWidth] = useState(380);

  const onResizeStart = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const handle = event.currentTarget;
    try {
      handle.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is unavailable for some synthetic events.
    }
    const startX = event.clientX;
    const startWidth = panelWidth;
    const rowWidth = rowRef.current?.getBoundingClientRect().width ?? startWidth + 320;

    const onMove = (moveEvent: PointerEvent) => {
      const next = startWidth - (moveEvent.clientX - startX);
      const max = Math.max(280, rowWidth - 320 - 12);
      setPanelWidth(Math.min(max, Math.max(280, next)));
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const handleExport = () => {
    if (!session) return;
    const blob = new Blob([buildFlowExport(session)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `sip-flow-${session.sid.replace(/[:/\\]/g, "_")}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!session) {
    return <div className="app-card p-6">{t.flowFailed}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <Link
            to={`/sessions?uploadId=${uploadId}`}
            className="inline-flex items-center gap-1 text-sm text-brand hover:underline mb-2"
          >
            <ArrowLeft size={16} />
            {t.back}
          </Link>
          <h1 className="app-page-title">{t.flowTitle}</h1>
          <p className="app-page-subtitle">{t.flowSubtitle(session.sid, session.flow.steps.length)}</p>
        </div>
        <button className="app-btn-secondary inline-flex items-center gap-2" onClick={handleExport}>
          <Download size={16} />
          {t.export}
        </button>
      </div>

      <div
        ref={rowRef}
        className="flex flex-col xl:flex-row min-h-[640px] gap-4 xl:gap-0"
        style={{ "--panel-width": `${panelWidth}px` } as React.CSSProperties}
      >
        <div className="flex-1 min-w-0 min-h-[480px]">
          <SipLadderDiagram
            flow={session.flow}
            selectedMessageId={selectedMessageId}
            onSelect={setSelectedMessageId}
          />
        </div>
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label={t.resizePanel}
          className="hidden xl:flex w-3 shrink-0 cursor-col-resize items-center justify-center"
          onPointerDown={onResizeStart}
        >
          <div className="h-16 w-1 rounded-full bg-gray-300 dark:bg-neutral-700" />
        </div>
        <div className="min-h-[480px] w-full shrink-0 xl:w-[var(--panel-width)]">
          <MessageDetailPanel message={message} />
        </div>
      </div>
    </div>
  );
}
