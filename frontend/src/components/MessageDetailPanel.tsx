import type { MessageDetail } from "@/api/client";
import { useLanguage } from "@/context/LanguageContext";

const HIGHLIGHT_HEADERS = ["call-id", "cseq", "via", "contact", "from", "to"];

interface Props {
  message: MessageDetail | null;
  loading?: boolean;
}

function messageTitle(message: MessageDetail, fallback: string): string {
  if (message.status_code != null) {
    return message.reason_phrase
      ? `${message.status_code} ${message.reason_phrase}`
      : `${message.status_code}`;
  }
  return message.method || fallback;
}

export default function MessageDetailPanel({ message, loading }: Props) {
  const { t } = useLanguage();

  if (loading) {
    return (
      <div className="app-card p-4 h-full">
        <p className="text-sm text-gray-500">{t.loadingMessage}</p>
      </div>
    );
  }

  if (!message) {
    return (
      <div className="app-card p-4 h-full">
        <p className="text-sm text-gray-500">{t.selectMessage}</p>
      </div>
    );
  }

  return (
    <div className="app-card p-4 h-full flex flex-col min-h-0">
      <div className="mb-4">
        <h2 className="font-semibold">
          {messageTitle(message, t.sipMessage)}
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {message.timestamp} · seq {message.sequence}
          {message.direction ? ` · ${message.direction}` : ""}
        </p>
      </div>

      <div className="flex-1 overflow-auto space-y-4 min-h-0">
        <div>
          <h3 className="text-sm font-medium mb-2">{t.headers}</h3>
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
            <h3 className="text-sm font-medium mb-2">{t.body}</h3>
            <pre className="text-xs font-mono bg-gray-50 dark:bg-neutral-950 p-3 rounded-lg overflow-auto">
              {message.body}
            </pre>
          </div>
        )}

        <div>
          <h3 className="text-sm font-medium mb-2">{t.raw}</h3>
          <pre className="text-xs font-mono bg-gray-50 dark:bg-neutral-950 p-3 rounded-lg overflow-auto whitespace-pre-wrap">
            {message.raw_text}
          </pre>
        </div>
      </div>
    </div>
  );
}
