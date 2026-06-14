import { createContext, useCallback, useContext, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Dialog } from "@/components/retroui/Dialog";
import { Button } from "@/components/retroui/Button";

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
}

interface ConfirmState extends ConfirmOptions {
  id: number;
  resolve: (value: boolean) => void;
}

interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue>({
  confirm: () => Promise.resolve(false),
});

export const useConfirm = () => useContext(ConfirmContext);

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [queue, setQueue] = useState<ConfirmState[]>([]);
  let _nextId = 0;

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      const id = Date.now() + _nextId++;
      setQueue((prev) => [...prev, { ...options, id, resolve }]);
    });
  }, []);

  const handleResolve = useCallback((id: number, value: boolean) => {
    setQueue((prev) => {
      const item = prev.find((s) => s.id === id);
      item?.resolve(value);
      return prev.filter((s) => s.id !== id);
    });
  }, []);

  const current = queue[0];

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {current && (
        <Dialog open onOpenChange={(open: boolean) => { if (!open) handleResolve(current.id, false); }}>
          <Dialog.Content size="sm">
            <Dialog.Header>
              <span className="flex items-center gap-2 text-sm font-bold">
                <AlertTriangle size={16} />
                {current.title ?? "确认操作"}
              </span>
            </Dialog.Header>
            <div className="px-4 py-4">
              <p className="text-sm">{current.message}</p>
            </div>
            <Dialog.Footer position="static">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleResolve(current.id, false)}
              >
                {current.cancelLabel ?? "取消"}
              </Button>
              <Button
                size="sm"
                className={current.destructive !== false ? "bg-red-600 text-white hover:bg-red-700 border-red-700" : ""}
                onClick={() => handleResolve(current.id, true)}
              >
                {current.confirmLabel ?? "确认"}
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog>
      )}
    </ConfirmContext.Provider>
  );
}
