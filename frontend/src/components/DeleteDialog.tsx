import { AlertTriangle, LoaderCircle, Trash2 } from "lucide-react";
import { useState } from "react";
import type { TunnelStatus } from "../lib/api";
import { Modal } from "./Modal";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  status: TunnelStatus | null;
  onConfirm: () => Promise<void>;
}

export function DeleteDialog({ open, onOpenChange, status, onConfirm }: Props) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const managed = status?.runtime.managed ?? false;

  const remove = async () => {
    setDeleting(true);
    setError(null);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="删除隧道"
      description="配置删除后无法从界面恢复。日志文件暂时保留。"
    >
      <div className="space-y-4 px-7 py-6">
        <div className="rounded-xl border border-[#efcaca] bg-[#fff6f6] p-4 text-sm leading-6 text-[#873f3f]">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={17} />
            确认删除 “{status?.tunnel.name}”？
          </div>
          <p className="mt-1 text-[#9b5d5d]">
            {managed
              ? "该隧道由 AutoSSH Desk 管理。请先返回页面停止隧道，再删除配置。"
              : "此操作不会终止远端其他会话，也不会删除远端端口。"}
          </p>
        </div>
        {error ? (
          <div className="rounded-xl border border-[#efcaca] bg-[#fff5f5] px-4 py-3 text-sm text-[#a33e3e]">
            {error}
          </div>
        ) : null}
      </div>
      <div className="flex justify-end gap-2 border-t border-[#e5e9e2] bg-[#f7f9f5] px-7 py-4">
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="h-10 rounded-xl border border-[#d7ded5] bg-white px-4 text-sm font-medium text-[#506058] hover:bg-[#f0f3ed]"
        >
          取消
        </button>
        <button
          type="button"
          disabled={managed || deleting}
          onClick={() => void remove()}
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#a73c3c] px-5 text-sm font-semibold text-white hover:bg-[#933333] disabled:cursor-not-allowed disabled:bg-[#d9c4c4]"
        >
          {deleting ? <LoaderCircle size={15} className="animate-spin" /> : <Trash2 size={15} />}
          删除配置
        </button>
      </div>
    </Modal>
  );
}

