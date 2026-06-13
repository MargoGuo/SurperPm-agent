type EventHandler = (data: unknown) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, EventHandler[]>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private url: string;

  constructor(workspaceId: string) {
    const base = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
    this.url = `${base}/ws/${workspaceId}`;
    this.connect();
  }

  private connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const handlers = this.handlers.get(msg.event) ?? [];
        handlers.forEach((h) => h(msg.data));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  on(event: string, handler: EventHandler) {
    const list = this.handlers.get(event) ?? [];
    list.push(handler);
    this.handlers.set(event, list);
    return () => {
      const updated = (this.handlers.get(event) ?? []).filter((h) => h !== handler);
      this.handlers.set(event, updated);
    };
  }

  close() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
