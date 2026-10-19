import { useMemo } from "react";
import type { FlowResponse } from "@/api/client";

interface Props {
  flow: FlowResponse;
  selectedMessageId: string | null;
  onSelect: (messageId: string) => void;
}

const COLUMN_WIDTH = 180;
const ROW_HEIGHT = 56;
const HEADER_HEIGHT = 48;
const PADDING_X = 40;

export default function SipLadderDiagram({ flow, selectedMessageId, onSelect }: Props) {
  const participantIndex = useMemo(() => {
    const map = new Map<string, number>();
    flow.participants.forEach((participant, index) => map.set(participant.id, index));
    return map;
  }, [flow.participants]);

  const width = Math.max(flow.participants.length * COLUMN_WIDTH + PADDING_X * 2, 480);
  const height = HEADER_HEIGHT + flow.steps.length * ROW_HEIGHT + 40;

  return (
    <div className="app-card p-4 overflow-auto h-full">
      <svg width={width} height={height} className="min-w-full">
        {flow.participants.map((participant, index) => {
          const x = PADDING_X + index * COLUMN_WIDTH + COLUMN_WIDTH / 2;
          return (
            <g key={participant.id}>
              <line
                x1={x}
                y1={HEADER_HEIGHT}
                x2={x}
                y2={height - 20}
                stroke="currentColor"
                className="text-gray-300 dark:text-neutral-700"
                strokeWidth={2}
              />
              <rect
                x={x - 70}
                y={12}
                width={140}
                height={28}
                rx={6}
                className="fill-brand/10 stroke-brand/30"
                strokeWidth={1}
              />
              <text
                x={x}
                y={30}
                textAnchor="middle"
                className="fill-current text-xs font-medium"
                style={{ fontSize: 11 }}
              >
                {truncate(participant.label, 18)}
              </text>
            </g>
          );
        })}

        {flow.steps.map((step, index) => {
          const fromIndex = participantIndex.get(step.from_participant) ?? 0;
          const toIndex = participantIndex.get(step.to_participant) ?? 0;
          const y = HEADER_HEIGHT + index * ROW_HEIGHT + ROW_HEIGHT / 2;
          const x1 = PADDING_X + fromIndex * COLUMN_WIDTH + COLUMN_WIDTH / 2;
          const x2 = PADDING_X + toIndex * COLUMN_WIDTH + COLUMN_WIDTH / 2;
          const isSelected = selectedMessageId === step.message_id;
          const sameColumn = fromIndex === toIndex;
          const left = Math.min(x1, x2);
          const arrowWidth = Math.abs(x2 - x1);
          const labelX = sameColumn ? x1 : left + arrowWidth / 2;
          const directionRight = x2 >= x1;
          const labelWidth = Math.max(72, step.label.length * 6.2 + 16);

          return (
            <g
              key={step.message_id}
              onClick={() => onSelect(step.message_id)}
              className="cursor-pointer"
            >
              {sameColumn ? null : (
                <line
                  x1={x1}
                  y1={y}
                  x2={x2}
                  y2={y}
                  stroke={isSelected ? "#0066cc" : step.is_request ? "#334155" : "#64748b"}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  strokeDasharray={step.is_request ? undefined : "6 4"}
                  markerEnd="url(#arrowhead)"
                />
              )}
              <rect
                x={labelX - labelWidth / 2}
                y={y - 22}
                width={labelWidth}
                height={18}
                rx={4}
                className={isSelected ? "fill-brand text-white" : "fill-white dark:fill-neutral-900"}
                stroke={isSelected ? "#0066cc" : "#cbd5e1"}
                strokeWidth={1}
              />
              <text
                x={labelX}
                y={y - 10}
                textAnchor="middle"
                className={isSelected ? "fill-white" : "fill-current"}
                style={{ fontSize: 10, fontWeight: 600 }}
              >
                {step.label}
              </text>
              <text
                x={sameColumn ? x1 : directionRight ? Math.max(x1, x2) + 8 : Math.min(x1, x2) - 8}
                y={y + 14}
                textAnchor={sameColumn ? "middle" : directionRight ? "start" : "end"}
                className="fill-gray-400"
                style={{ fontSize: 9 }}
              >
                {step.timestamp}
              </text>
            </g>
          );
        })}

        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" className="fill-slate-500" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}
