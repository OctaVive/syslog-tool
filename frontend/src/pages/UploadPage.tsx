import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FileUp, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { uploadSyslog, type UploadResponse } from "@/api/client";

export default function UploadPage() {
  const navigate = useNavigate();
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const mutation = useMutation({
    mutationFn: uploadSyslog,
    onSuccess: (data) => {
      setResult(data);
      sessionStorage.setItem("lastUploadId", data.id);
    },
  });

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      mutation.mutate(file);
    },
    [mutation],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="app-page-title">Syslog uploaden</h1>
        <p className="app-page-subtitle">
          Upload een AudioCodes syslog bestand om SIP-sessies te analyseren.
        </p>
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
            <p className="font-medium">Sleep een syslog bestand hierheen</p>
            <p className="text-sm text-gray-500 dark:text-neutral-400 mt-1">of kies een .log / .txt bestand</p>
          </div>
          <label className="app-btn-primary cursor-pointer">
            Bestand kiezen
            <input
              type="file"
              accept=".log,.txt,.syslog"
              className="hidden"
              onChange={(event) => handleFile(event.target.files?.[0])}
            />
          </label>
        </div>
      </div>

      {mutation.isError && (
        <div className="app-card p-4 border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
          Upload mislukt: {(mutation.error as Error).message}
        </div>
      )}

      {result && (
        <div className="app-card p-6 space-y-4">
          <h2 className="text-lg font-semibold">Parse resultaat</h2>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Bestand</dt>
              <dd className="font-medium truncate">{result.filename}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Sessies</dt>
              <dd className="font-medium">{result.session_count}</dd>
            </div>
            <div>
              <dt className="text-gray-500">SIP berichten</dt>
              <dd className="font-medium">{result.message_count}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Warnings</dt>
              <dd className="font-medium">{result.parse_warnings.length}</dd>
            </div>
          </dl>

          {result.parse_warnings.length > 0 && (
            <div className="text-sm">
              <p className="font-medium mb-2">Parse warnings</p>
              <ul className="list-disc pl-5 space-y-1 text-gray-600 dark:text-neutral-400 max-h-32 overflow-auto">
                {result.parse_warnings.slice(0, 10).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            className="app-btn-primary"
            onClick={() => navigate(`/sessions?uploadId=${result.id}`)}
          >
            Bekijk sessies
          </button>
        </div>
      )}
    </div>
  );
}
