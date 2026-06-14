import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle, XCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });
export const useToast = () => useContext(ToastContext);

const ICONS: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
};

const COLORS: Record<ToastType, string> = {
  success: "border-green-600 bg-green-50 text-green-800",
  error: "border-red-600 bg-red-50 text-red-800",
  info: "border-blue-600 bg-blue-50 text-blue-800",
};

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: number) => void }) {
  const Icon = ICONS[t.type];
  return (
    <div
      className={cn(
        "flex items-center gap-2 border-2 px-4 py-3 shadow-[3px_3px_0_0_#000] text-sm animate-in slide-in-from-right-full duration-300",
        COLORS[t.type],
      )}
    >
      <Icon size={16} className="shrink-0" />
      <span className="flex-1">{t.message}</span>
      <button onClick={() => onDismiss(t.id)} className="shrink-0 opacity-60 hover:opacity-100">
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let _nextId = 0;

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + _nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {toasts.length > 0 && (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
          {toasts.map((t) => (
            <ToastItem key={t.id} t={t} onDismiss={dismiss} />
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}
