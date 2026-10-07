import type { AskResponse, DocumentDetail, DocumentSummary, StreamEvent, User } from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0] as { msg?: string };
      if (first.msg) return first.msg;
    }
  } catch {
    /* body was not JSON */
  }
  return response.status === 401 ? "Sign in to continue." : "Request failed.";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  if (!response.ok) throw new ApiError(response.status, await parseError(response));
  return (await response.json()) as T;
}

export const api = {
  me: () => request<User>("/auth/me"),
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  documents: () => request<DocumentSummary[]>("/documents"),
  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  remove: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  addText: (text: string, title?: string) =>
    request<DocumentSummary>("/documents", {
      method: "POST",
      body: JSON.stringify({ source_type: "text", text, title: title || null }),
    }),
  addUrl: (url: string, title?: string) =>
    request<DocumentSummary>("/documents", {
      method: "POST",
      body: JSON.stringify({ source_type: "url", url, title: title || null }),
    }),
  upload: (file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<DocumentSummary>("/documents/upload", { method: "POST", body });
  },
  ask: (question: string) =>
    request<AskResponse>("/ask", { method: "POST", body: JSON.stringify({ question }) }),
};

export async function askStream(question: string, onEvent: (event: StreamEvent) => void): Promise<void> {
  const response = await fetch("/ask/stream", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new ApiError(response.status, await parseError(response));
  if (!response.body) throw new ApiError(500, "The answer stream did not start.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(5).trim()) as StreamEvent);
    }
  }
}
