import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  width?: "wide" | "normal";
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  width = "normal",
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content"
          style={{ width: width === "wide" ? "min(860px, calc(100vw - 80px))" : undefined }}
        >
          <div className="flex items-start justify-between border-b border-[#e5e9e2] px-7 py-6">
            <div>
              <Dialog.Title className="text-xl font-semibold tracking-[-0.02em] text-[#15251d]">
                {title}
              </Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-1 text-sm leading-6 text-[#6c7a71]">
                  {description}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="关闭"
                className="rounded-full border border-[#dfe5dc] bg-white p-2 text-[#65736a] transition hover:bg-[#f1f4ee]"
              >
                <X size={17} />
              </button>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

