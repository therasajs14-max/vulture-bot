export type Role = "user" | "assistant" | "system" | "tool";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  is_admin: boolean;
  is_superadmin: boolean;
  theme: string;
  ai_provider?: string;
  ai_model?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  is_archived: boolean;
  is_pinned: boolean;
  updated_at: string;
  last_message?: string;
}

export interface MessageItem {
  id: string;
  role: Role;
  content: string;
  is_error?: boolean;
  created_at?: string;
}

export interface FilePreviewStats {
  total_rows: number;
  valid_emails: number;
  missing_emails: number;
  invalid_emails: number;
  duplicate_emails: number;
  rows_requiring_review: number;
}

export interface FilePreviewData {
  filename: string;
  total_rows: number;
  columns: string[];
  field_mappings: Record<string, string | null>;
  stats: FilePreviewStats;
  sample_rows: Array<{
    row_index: number;
    data: Record<string, any>;
    is_valid: boolean;
    error?: string;
  }>;
  raw_text_preview?: string;
}

export interface EmailDraftReview {
  draft_id: string;
  task_name: string;
  subject: string;
  body_template: string;
  is_personalized: boolean;
  content_hash: string;
  status: string;
  recipient_count: number;
  excluded_count: number;
  recipients_sample: Array<{
    name: string;
    email: string;
    department?: string;
    year?: string;
  }>;
  excluded_sample: Array<{
    name: string;
    email: string;
    reason: string;
  }>;
  sample_preview?: {
    recipient: any;
    rendered_body: string;
  };
  approval?: {
    status: string;
    approver_id?: string;
    decided_at?: string;
    reason?: string;
  };
}

export interface BatchResultRecipient {
  id: string;
  email: string;
  name?: string;
  status: string;
  error?: string;
  sent_at?: string;
}

export interface BatchResults {
  batch_id: string;
  status: string;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  email_provider: string;
  recipients: BatchResultRecipient[];
}
