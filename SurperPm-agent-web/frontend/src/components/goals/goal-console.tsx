import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

const THEME = {
  background: "#171717",
  foreground: "#e5e5e5",
  cursor: "#e5e5e5",
  black: "#171717",
  brightBlack: "#525252",
};

function wsUrl(goalId: number): string {
  const base = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
  return `${base}/ws/goal/${goalId}/term`;
}

export function GoalConsole({ goalId }: { goalId: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const term = new Terminal({
      fontFamily: "monospace",
      fontSize: 13,
      cursorBlink: true,
      theme: THEME,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(container);
    fit.fit();

    const ws = new WebSocket(wsUrl(goalId));

    const sendResize = () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }));
      }
    };

    ws.onopen = () => {
      setConnected(true);
      sendResize();
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "data") {
          term.write(msg.data);
        } else if (msg.type === "exit") {
          term.write("\r\n\x1b[2m[session ended]\x1b[0m\r\n");
        } else if (msg.type === "error") {
          term.write(`\r\n\x1b[31m[error] ${msg.message}\x1b[0m\r\n`);
        }
      } catch {
        // ignore malformed frames
      }
    };
    ws.onclose = () => setConnected(false);

    const dataSub = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "data", data }));
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      fit.fit();
      sendResize();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      dataSub.dispose();
      ws.close();
      term.dispose();
    };
  }, [goalId]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-2 py-1 border-b-2 border-border bg-muted/30 shrink-0">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`}
          title={connected ? "connected" : "disconnected"}
        />
        <span className="text-xs text-muted-foreground font-mono">
          goal-{goalId} workdir
        </span>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0 bg-neutral-900 p-1" />
    </div>
  );
}
