import { Circle } from "lucide-react";
import type { TunnelState } from "../lib/api";
import { stateMeta } from "../lib/format";

const tones = {
  green: "border-[#c6e2ce] bg-[#e9f6ed] text-[#21693d]",
  amber: "border-[#ecd8a8] bg-[#fbf3df] text-[#8b6417]",
  red: "border-[#eccaca] bg-[#fbeaea] text-[#a23535]",
  gray: "border-[#dce2dc] bg-[#f1f4f0] text-[#637068]",
};

const dots = {
  green: "fill-[#2e8b52] text-[#2e8b52]",
  amber: "fill-[#c18b22] text-[#c18b22]",
  red: "fill-[#c54a4a] text-[#c54a4a]",
  gray: "fill-[#88958c] text-[#88958c]",
};

export function StatusBadge({
  state,
  compact = false,
}: {
  state: TunnelState;
  compact?: boolean;
}) {
  const meta = stateMeta[state];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${tones[meta.tone]} ${
        compact ? "px-2 py-0.5 text-[11px]" : "px-3 py-1.5 text-xs"
      }`}
    >
      <Circle
        size={7}
        className={`${dots[meta.tone]} ${
          state === "starting" || state === "reconnecting" ? "status-pulse" : ""
        }`}
      />
      {meta.label}
    </span>
  );
}

export function StatusDot({ state }: { state: TunnelState }) {
  const meta = stateMeta[state];
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        meta.tone === "green"
          ? "bg-[#64c684] shadow-[0_0_0_4px_rgba(100,198,132,0.12)]"
          : meta.tone === "amber"
            ? "bg-[#e0a536] shadow-[0_0_0_4px_rgba(224,165,54,0.12)]"
            : meta.tone === "red"
              ? "bg-[#df6d6d] shadow-[0_0_0_4px_rgba(223,109,109,0.12)]"
              : "bg-[#829087]"
      } ${state === "starting" || state === "reconnecting" ? "status-pulse" : ""}`}
    />
  );
}

