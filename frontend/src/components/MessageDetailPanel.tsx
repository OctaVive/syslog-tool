import type { MessageDetail } from "@/api/client";

const HIGHLIGHT_HEADERS = ["call-id", "cseq", "via", "contact", "from", "to"];

interface Props {
  message: MessageDetail | null;
  loading?: boolean;
}

export default function MessageDetailPanel({ message, loading }: Props) {
  if (loading) {
    return (
      <div className="app-card p-4 h-full">
        <p className="text-sm text-gray-500">Bericht laden...</p>
      </div>
    );
  }

  if (!message) {
    return (
      <div className="app-card p-4 h-full">
        <p className="text-sm text-gray-500">Selecteer een bericht in het ladder diagram.</p>
      </div>
    );
  }

  return (
    <div className="app-card p-4 h-full flex flex-col min-h-0">
      <div className="mb-4">
        <h2 className="font-semibold">
          {message.method || (message.status_code ? `${message.status_code}` : "SIP bericht")}
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {message.timestamp} · seq {message.sequence}
          {message.direction ? ` · ${message.direction}` : ""}
        </p>
      </div>

      <div className="flex-1 overflow-auto space-y-4 min-h-0">
        <div>
          <h3 className="text-sm font-medium mb-2">Headers</h3>
          <table className="w-full text-xs">
            <tbody>
              {Object.entries(message.headers).map(([key, value]) => (
                <tr
                  key={key}
                  className={`border-t border-gray-100 dark:border-neutral-800 ${
                    HIGHLIGHT_HEADERS.includes(key.toLowerCase()) ? "bg-brand/5" : ""
                  }`}
                >
                  <td className="py-2 pr-3 font-mono text-gray-500 align-top whitespace-nowrap">{key}</td>
                  <td className="py-2 font-mono break-all">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {message.body && (
          <div>
            <h3 className="text-sm font-medium mb-2">Body</h3>
            <pre className="text-xs font-mono bg-gray-50 dark:bg-neutral-950 p-3 rounded-lg overflow-auto">
              {message.body}
            </pre>
          </div>
        )}

        <div>
          <h3 className="text-sm font-medium mb-2">Raw</h3>
          <pre className="text-xs font-mono bg-gray-50 dark:bg-neutral-950 p-3 rounded-lg overflow-auto whitespace-pre-wrap">
            {message.raw_text}
          </pre>
        </div>
      </div>
    </div>
  );
}
