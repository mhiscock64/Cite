export type User = {
  id: string;
  email: string;
  created_at: string;
};

export type DocStatus = "queued" | "ready" | "failed";

export type DocumentSummary = {
  id: string;
  title: string;
  source_type: "text" | "url" | "file";
  source_url: string | null;
  status: DocStatus;
  error: string | null;
  created_at: string;
  chunk_count: number;
};

export type Chunk = {
  id: string;
  position: number;
  heading: string | null;
  text: string;
};

export type DocumentDetail = DocumentSummary & {
  chunks: Chunk[];
};

export type Citation = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  heading: string | null;
  position: number;
  text: string;
  score: number;
};

export type AskReason = "nothing_matched" | "unsupported" | "model_unreachable" | null;

export type AskResponse = {
  id: string;
  question: string;
  answer: string;
  refused: boolean;
  reason: AskReason;
  citations: Citation[];
};

export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "refusal"; reason: "nothing_matched" | "unsupported"; answer: string; id: string; citations: [] }
  | {
      type: "done";
      id: string;
      answer: string;
      refused: boolean;
      reason: AskReason;
      citations: Citation[];
    };
