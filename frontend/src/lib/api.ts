import {
  UserProfile,
  ConversationSummary,
  MessageItem,
  FilePreviewData,
  EmailDraftReview,
  BatchResults,
} from "./types";

const API_BASE = "http://localhost:8000";

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    if (typeof window !== "undefined") {
      localStorage.setItem("vulture_token", token);
    }
  } else {
    if (typeof window !== "undefined") {
      localStorage.removeItem("vulture_token");
    }
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("vulture_token");
  }
  return authToken;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include", // send cookies
  });

  if (!res.ok) {
    let errorDetail = `Request failed (${res.status})`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // Auth
  async getMe(): Promise<UserProfile> {
    return request<UserProfile>("/api/auth/me");
  },

  async demoLogin(email = "admin@vulture.local", name = "Administrator", isAdmin = true) {
    const data = await request<{ success: boolean; token: string; user: any }>("/api/auth/demo-login", {
      method: "POST",
      body: JSON.stringify({ email, name, is_admin: isAdmin }),
    });
    if (data.token) {
      setAuthToken(data.token);
    }
    return data;
  },

  async logout() {
    await request("/api/auth/logout", { method: "POST" });
    setAuthToken(null);
  },

  async getGoogleAuthUrl() {
    return request<{ configured: boolean; url?: string; message?: string }>("/api/auth/google/url");
  },

  // Conversations
  async listConversations(): Promise<ConversationSummary[]> {
    return request<ConversationSummary[]>("/api/conversations");
  },

  async createConversation(title = "New Conversation"): Promise<ConversationSummary> {
    return request<ConversationSummary>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  async getConversation(id: string): Promise<{
    id: string;
    title: string;
    messages: MessageItem[];
  }> {
    return request(`/api/conversations/${id}`);
  },

  async updateConversation(id: string, updates: { title?: string; is_archived?: boolean; is_pinned?: boolean }) {
    return request(`/api/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  async deleteConversation(id: string) {
    return request(`/api/conversations/${id}`, { method: "DELETE" });
  },

  // Files & Datasets
  async uploadFile(file: File, conversationId?: string): Promise<{
    file_id: string;
    filename: string;
    preview: FilePreviewData;
  }> {
    const formData = new FormData();
    formData.append("file", file);
    if (conversationId) {
      formData.append("conversation_id", conversationId);
    }
    return request("/api/files/upload", {
      method: "POST",
      body: formData,
    });
  },

  async importDataset(fileId: string, name: string, fieldMappings: Record<string, string>) {
    return request("/api/datasets/import", {
      method: "POST",
      body: JSON.stringify({
        file_id: fileId,
        name,
        field_mappings: fieldMappings,
      }),
    });
  },

  async queryDataset(datasetId: string, filters: { department?: string; year?: string; valid_only?: boolean }) {
    const params = new URLSearchParams();
    if (filters.department) params.set("department", filters.department);
    if (filters.year) params.set("year", filters.year);
    if (filters.valid_only !== undefined) params.set("valid_only", String(filters.valid_only));
    return request(`/api/datasets/${datasetId}/query?${params.toString()}`);
  },

  // Email & Approvals
  async createDraft(payload: {
    task_name: string;
    subject: string;
    body_template: string;
    dataset_id?: string;
    conversation_id?: string;
    is_personalized?: boolean;
    selection_description?: string;
  }): Promise<{ success: boolean; draft: EmailDraftReview }> {
    return request("/api/email/drafts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async reviewDraft(draftId: string): Promise<EmailDraftReview> {
    return request<EmailDraftReview>(`/api/email/drafts/${draftId}/review`);
  },

  async updateDraft(draftId: string, payload: { subject?: string; body_template?: string; task_name?: string }) {
    return request(`/api/email/drafts/${draftId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async approveDraft(draftId: string, reason = "Approved by administrator.") {
    return request(`/api/email/drafts/${draftId}/approve`, {
      method: "POST",
      body: JSON.stringify({ decision_reason: reason }),
    });
  },

  async dispatchBatch(draftId: string, idempotencyKey?: string) {
    return request<{ success: boolean; batch_id: string; total_recipients: number; sent_count: number }>(
      `/api/email/drafts/${draftId}/dispatch`,
      {
        method: "POST",
        body: JSON.stringify({ idempotency_key: idempotencyKey }),
      }
    );
  },

  async getBatchResults(batchId: string): Promise<BatchResults> {
    return request<BatchResults>(`/api/email/batches/${batchId}/results`);
  },

  async getAuditTrail() {
    return request<any[]>("/api/email/audit");
  },

  // Real Email Configuration & Live Test
  async getEmailConfig() {
    return request<{
      provider: string;
      smtp_host?: string;
      smtp_port?: number;
      smtp_username?: string;
      smtp_use_tls?: boolean;
      is_configured: boolean;
    }>("/api/system/email-config");
  },

  async configureEmail(payload: {
    provider: "smtp" | "mock";
    smtp_host?: string;
    smtp_port?: number;
    smtp_username?: string;
    smtp_password?: string;
    smtp_use_tls?: boolean;
  }) {
    return request("/api/system/configure-email", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async sendTestEmail(toEmail: string) {
    return request<{
      success: boolean;
      provider: string;
      message_id: string;
      sent_to: string;
      delivery_note: string;
    }>("/api/system/test-email", {
      method: "POST",
      body: JSON.stringify({ to_email: toEmail }),
    });
  },

  // System
  async getAiStatus() {
    return request<{
      active_provider: string;
      is_ready: boolean;
      providers: {
        gemini: { available: boolean; default_model: string; models: string[] };
        ollama: { available: boolean; base_url: string; default_model: string; models: string[] };
      };
    }>("/api/system/ai-status");
  },

  // SSE Chat stream helper
  streamChat(
    conversationId: string,
    message: string,
    onChunk: (content: string) => void,
    onError: (err: string) => void,
    onDone: () => void,
    modelProvider?: string,
    modelName?: string
  ): () => void {
    const token = getAuthToken();
    const abortController = new AbortController();

    fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: "include",
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        model_provider: modelProvider,
        model_name: modelName,
      }),
      signal: abortController.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Chat stream error: ${res.statusText}`);
        }
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No readable stream");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const block of lines) {
            const dataMatch = block.match(/data:\s*(.*)/);
            if (dataMatch) {
              try {
                const parsed = JSON.parse(dataMatch[1]);
                if (parsed.content) {
                  onChunk(parsed.content);
                }
                if (parsed.error) {
                  onError(parsed.error);
                }
                if (parsed.done) {
                  onDone();
                }
              } catch {
                // ignore unparseable block
              }
            }
          }
        }
        onDone();
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          onError(err.message || "Network error");
        }
      });

    return () => abortController.abort();
  },
};
