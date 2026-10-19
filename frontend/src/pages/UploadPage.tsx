import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FileUp, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { clearAnalysis, loadAnalysis, uploadSyslog, type AnalysisResponse } from "@/api/client";
import { useLanguage } from "@/context/LanguageContext";

export default function UploadPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [dragOver, setDragOver] = useState(false);
  const [pasted, setPasted] = useState("");
  const [result, setResult] = useState<AnalysisResponse | null>(() => loadAnalysis());

  const mutation = useMutation({
    mutationFn: uploadSyslog,
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      mutation.mutate(file);
    },
    [mutation],
  );

  const handlePaste = () => {
    const text = pasted.trim();
    if (!text) return;
    const file = new File([pasted], "pasted.syslog", { type: "text/plain" });
    mutation.mutate(file);
  };

  const handleClear = () => {
    setPasted("");
    setResult(null);
    mutation.reset();
    clearAnalysis();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="app-page-title">{t.uploadTitle}</h1>
        <p className="app-page-subtitle">{t.uploadSubtitle}</p>
      </div>

      <div
        className={`app-card p-8 border-dashed border-2 transition-colors ${
          dragOver ? "border-brand bg-brand/5" : "border-gray-300 dark:border-neutral-700"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragOver(false);
          handleFile(event.dataTransfer.files[0]);
        }}
      >
        <div className="flex flex-col items-center text-center gap-4">
          <div className="p-4 rounded-full bg-brand/10 text-brand">
            {mutation.isPending ? <Loader2 className="animate-spin" size={32} /> : <FileUp size={32} />}
          </div>
          <div>
            <p className="font-medium">{t.drop}</p>
            <p className="text-sm text-gray-500 mt-1">{t.dropHint}</p>
          </div>
          <label className="app-btn-primary cursor-pointer">
            {t.chooseFile}
            <input
              type="file"
              accept=".log,.txt,.syslog"
              className="hidden"
              onChange={(event) => handleFile(event.target.files?.[0])}
            />
          </label>
        </div>
      </div>

      <div className="app-card p-6 space-y-4">
        <div>
          <label htmlFor="syslog-paste" className="font-medium">
            {t.pasteTitle}
          </label>
          <p className="text-sm text-gray-500 mt-1">{t.pasteHint}</p>
        </div>
        <textarea
          id="syslog-paste"
          className="app-input min-h-48 font-mono text-xs"
          placeholder={t.pastePlaceholder}
          value={pasted}
          onChange={(event) => setPasted(event.target.value)}
        />
        <button
          className="app-btn-primary"
          type="button"
          disabled={!pasted.trim() || mutation.isPending}
          onClick={handlePaste}
        >
          {t.analyze}
        </button>
      </div>

      {mutation.isError && (
        <div className="app-card p-4 border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
          {t.uploadFailed}: {(mutation.error as Error).message}
        </div>
      )}

      {result && (
        <div className="app-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">{t.result}</h2>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">{t.file}</dt>
              <dd className="font-medium truncate">{result.filename}</dd>
            </div>
            <div>
              <dt className="text-gray-500">{t.sessions}</dt>
              <dd className="font-medium">{result.session_count}</dd>
            </div>
            <div>
              <dt className="text-gray-500">{t.sipMessages}</dt>
              <dd className="font-medium">{result.message_count}</dd>
            </div>
            <div>
              <dt className="text-gray-500">{t.warnings}</dt>
              <dd className="font-medium">{result.parse_warnings.length}</dd>
            </div>
          </dl>

          {result.parse_warnings.length > 0 && (
            <div className="text-sm">
              <p className="font-medium mb-2">{t.parseWarnings}</p>
              <ul className="list-disc pl-5 space-y-1 text-gray-600 dark:text-neutral-400 max-h-32 overflow-auto">
                {result.parse_warnings.slice(0, 10).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              className="app-btn-primary"
              onClick={() => navigate(`/sessions?uploadId=${result.id}`)}
            >
              {t.viewSessions}
            </button>
            <button className="app-btn-secondary" type="button" onClick={handleClear}>
              {t.clear}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
