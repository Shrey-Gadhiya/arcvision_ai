import axios from 'axios';

const getApiBaseUrl = (): string => {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && (window as any).__ARCVISION_API_BASE_URL__) {
    return (window as any).__ARCVISION_API_BASE_URL__.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    if (port === '5173') {
      return `${protocol}//${hostname}:8000`;
    }
    return `${protocol}//${hostname}${port ? `:${port}` : ''}`;
  }
  return 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const API_V1 = `${API_BASE_URL}/api/v1`;

export const getMediaUrl = (path?: string): string => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:') || path.startsWith('blob:')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
};

export const apiClient = axios.create({
  baseURL: API_V1,
  timeout: 60000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('arc_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    if (config.headers && typeof (config.headers as any).delete === 'function') {
      (config.headers as any).delete('Content-Type');
      (config.headers as any).delete('content-type');
    } else if (config.headers) {
      delete config.headers['Content-Type'];
      delete config.headers['content-type'];
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      const requestUrl = error?.config?.url || '';
      // Only clear storage and trigger re-auth if it's not the login attempt itself
      if (!requestUrl.includes('/auth/login') && !requestUrl.includes('/auth/token')) {
        localStorage.removeItem('arc_token');
        localStorage.removeItem('arc_user');
        localStorage.removeItem('arc_role');
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('arc_auth_expired'));
        }
      }
    }
    return Promise.reject(error);
  }
);

// WebSocket Real-time Listener
type EventHandler = (payload: any) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectInterval: any = null;

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    let wsUrl: string;
    if (API_BASE_URL.startsWith('https://')) {
      wsUrl = `${API_BASE_URL.replace('https://', 'wss://')}/ws`;
    } else if (API_BASE_URL.startsWith('http://')) {
      wsUrl = `${API_BASE_URL.replace('http://', 'ws://')}/ws`;
    } else {
      const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const hostname = typeof window !== 'undefined' && window.location ? window.location.hostname : 'localhost';
      wsUrl = `${wsProtocol}//${hostname}:8000/ws`;
    }
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[ARC VISION WS] Connected to tactical command server');
      if (this.reconnectInterval) {
        clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const topic = message.topic;
        if (topic && this.handlers.has(topic)) {
          this.handlers.get(topic)?.forEach((handler) => handler(message.data));
        }
        if (this.handlers.has('*')) {
          this.handlers.get('*')?.forEach((handler) => handler(message));
        }
      } catch (e) {
        // console.error('[WS Parse Error]', e);
      }
    };

    this.ws.onclose = () => {
      if (!this.reconnectInterval) {
        this.reconnectInterval = setInterval(() => {
          this.connect();
        }, 3000);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  on(topic: string, handler: EventHandler) {
    if (!this.handlers.has(topic)) {
      this.handlers.set(topic, new Set());
    }
    this.handlers.get(topic)?.add(handler);
    return () => {
      this.handlers.get(topic)?.delete(handler);
    };
  }
}

export const wsManager = new WebSocketManager();
