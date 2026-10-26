"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { EmailDraftReview, BatchResults, UserProfile } from "@/lib/types";
import {
  ShieldAlert,
  ShieldCheck,
  Mail,
  Send,
  X,
  Edit3,
  Check,
  AlertTriangle,
  Users,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Settings,
} from "lucide-react";

interface DraftApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  draftId: string | null;
  user: UserProfile | null;
  onBatchSent?: (results: BatchResults) => void;
}

export const DraftApprovalModal: React.FC<DraftApprovalModalProps> = ({
  isOpen,
  onClose,
  draftId,
  user,
  onBatchSent,
}) => {
  const [draft, setDraft] = useState<EmailDraftReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [subject, setSubject] = useState("");
  const [bodyTemplate, setBodyTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [batchResults, setBatchResults] = useState<BatchResults | null>(null);

  // Email provider & SMTP quick settings
  const [emailConfig, setEmailConfig] = useState<any>(null);
  const [showSmtpConfig, setShowSmtpConfig] = useState(false);
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [savingSmtp, setSavingSmtp] = useState(false);
  const [smtpStatusMessage, setSmtpStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && draftId) {
      loadDraft(draftId);
      loadEmailConfig();
    } else {
      setDraft(null);
      setBatchResults(null);
      setError(null);
      setShowSmtpConfig(false);
      setSmtpStatusMessage(null);
    }
  }, [isOpen, draftId]);

  const loadEmailConfig = async () => {
    try {
      const cfg = await api.getEmailConfig();
      setEmailConfig(cfg);
      if (cfg.smtp_host) setSmtpHost(cfg.smtp_host);
      if (cfg.smtp_port) setSmtpPort(cfg.smtp_port);
      if (cfg.smtp_username) setSmtpUsername(cfg.smtp_username);
      if (cfg.smtp_use_tls !== undefined) setSmtpUseTls(cfg.smtp_use_tls);
    } catch {
      // ignore
    }
  };

  const handleSaveSmtp = async (mode: "smtp" | "mock") => {
    setSavingSmtp(true);
    setSmtpStatusMessage(null);

    let cleanHost = smtpHost.trim();
    if (cleanHost.toLowerCase().includes("gmail") || cleanHost.includes("@")) {
      cleanHost = "smtp.gmail.com";
      setSmtpHost("smtp.gmail.com");
    } else if (cleanHost.toLowerCase().includes("outlook") || cleanHost.toLowerCase().includes("hotmail")) {
      cleanHost = "smtp.office365.com";
      setSmtpHost("smtp.office365.com");
    }

    let cleanUsername = smtpUsername.trim();
    if (mode === "smtp") {
      if (cleanHost === "smtp.gmail.com" && !cleanUsername.includes("@")) {
        setSavingSmtp(false);
        setSmtpStatusMessage(`❌ Username "${cleanUsername}" is missing @gmail.com. Please enter your full email address (e.g. ${cleanUsername}@gmail.com).`);
        return;
      }
    }

    try {
      await api.configureEmail({
        provider: mode,
        smtp_host: cleanHost,
        smtp_port: Number(smtpPort),
        smtp_username: cleanUsername,
        smtp_password: smtpPassword,
        smtp_use_tls: smtpUseTls,
      });
      await loadEmailConfig();
      setSmtpStatusMessage(
        mode === "smtp"
          ? "✅ Real SMTP configured! Emails will be sent to real student inboxes."
          : "✅ Switched to Simulation / Mock Mode."
      );
      if (mode === "mock") setShowSmtpConfig(false);
    } catch (err: any) {
      setSmtpStatusMessage("❌ Failed: " + (err.message || "Could not save settings"));
    } finally {
      setSavingSmtp(false);
    }
  };

  const loadDraft = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.reviewDraft(id);
      setDraft(data);
      setSubject(data.subject);
      setBodyTemplate(data.body_template);
    } catch (err: any) {
      setError(err.message || "Failed to load email draft.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSaveEdits = async () => {
    if (!draftId) return;
    try {
      const res = (await api.updateDraft(draftId, {
        subject,
        body_template: bodyTemplate,
      })) as any;
      setDraft(res.draft);
      setIsEditing(false);
    } catch (err: any) {
      setError(err.message || "Failed to save edits.");
    }
  };

  const handleApprove = async () => {
    if (!draftId) return;
    setApproving(true);
    setError(null);
    try {
      await api.approveDraft(draftId, "Admin explicitly approved email broadcast.");
      await loadDraft(draftId);
    } catch (err: any) {
      setError(err.message || "Approval failed.");
    } finally {
      setApproving(false);
    }
  };

  const handleDispatch = async () => {
    if (!draftId) return;
    setDispatching(true);
    setError(null);
    try {
      const dispatchRes = await api.dispatchBatch(draftId);
      const results = await api.getBatchResults(dispatchRes.batch_id);
      setBatchResults(results);
      if (onBatchSent) {
        onBatchSent(results);
      }
    } catch (err: any) {
      setError(err.message || "Batch sending failed.");
    } finally {
      setDispatching(false);
    }
  };

  const isApproved = draft?.approval?.status === "approved" || draft?.status === "approved";
  const isAdmin = user?.is_admin || user?.is_superadmin;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-3xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-950/40">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400">
              <Mail className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">
                  Admin Email Review & Broadcast Approval
                </span>
                {isApproved ? (
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Approved
                  </span>
                ) : (
                  <span className="text-[10px] bg-amber-500/20 text-amber-300 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
                    <ShieldAlert className="w-3 h-3" /> Pending Admin Approval
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-400">
                {draft?.task_name || "Task Dispatch"}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="py-16 text-center text-gray-400 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-400" />
              <span>Loading draft preview and recipient rules...</span>
            </div>
          ) : batchResults ? (
            /* Results Screen */
            <div className="space-y-4">
              <div className="p-4 bg-emerald-950/30 border border-emerald-800/60 rounded-xl text-center space-y-1">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <h4 className="text-sm font-bold text-emerald-200">Broadcast Dispatched Successfully</h4>
                <p className="text-gray-400">
                  Processed {batchResults.total_recipients} recipients via {batchResults.email_provider.toUpperCase()} provider.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="p-3 bg-gray-950 border border-gray-800 rounded-xl">
                  <span className="text-gray-400 block">Sent Successfully</span>
                  <span className="text-xl font-bold text-emerald-400">{batchResults.sent_count}</span>
                </div>
                <div className="p-3 bg-gray-950 border border-gray-800 rounded-xl">
                  <span className="text-gray-400 block">Failures</span>
                  <span className="text-xl font-bold text-rose-400">{batchResults.failed_count}</span>
                </div>
              </div>

              {/* Per-recipient breakdown */}
              <div className="border border-gray-800 rounded-xl overflow-hidden">
                <div className="bg-gray-950 p-2 font-semibold text-gray-300">Delivery Log</div>
                <div className="max-h-48 overflow-y-auto divide-y divide-gray-800 bg-gray-900/60">
                  {batchResults.recipients.map((r) => (
                    <div key={r.id} className="p-2.5 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-medium text-gray-200">{r.name || r.email}</span>
                        <span className="text-gray-500 block text-[11px]">{r.email}</span>
                      </div>
                      <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded text-[10px] font-semibold">
                        {r.status.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : draft ? (
            /* Review & Approval Screen */
            <div className="space-y-4">
              {/* Provider Status & Quick Real Email Toggle */}
              <div className={`p-3.5 rounded-xl border flex flex-col gap-2 transition ${
                emailConfig?.provider === "smtp"
                  ? "bg-emerald-950/30 border-emerald-800/60"
                  : "bg-amber-950/30 border-amber-800/60"
              }`}>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2.5">
                    {emailConfig?.provider === "smtp" ? (
                      <span className="flex h-2.5 w-2.5 relative">
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400"></span>
                      </span>
                    ) : (
                      <span className="flex h-2.5 w-2.5 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                      </span>
                    )}
                    <div>
                      <span className="font-bold text-xs text-white">
                        {emailConfig?.provider === "smtp"
                          ? "🟢 REAL EMAIL DELIVERY (SMTP Enabled)"
                          : "⚠️ SIMULATION MODE (Mock Provider)"}
                      </span>
                      <p className="text-[11px] text-gray-300">
                        {emailConfig?.provider === "smtp"
                          ? `Broadcasting via ${emailConfig.smtp_username || emailConfig.smtp_host} directly to student inboxes.`
                          : "Emails are recorded in database logs, but NOT sent to real recipient inboxes."}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowSmtpConfig(!showSmtpConfig)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-white border border-gray-700 transition flex items-center gap-1.5"
                  >
                    <Settings className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{showSmtpConfig ? "Hide Settings" : emailConfig?.provider === "smtp" ? "Edit SMTP" : "Configure Real Email"}</span>
                  </button>
                </div>

                {/* Inline SMTP Settings form */}
                {showSmtpConfig && (
                  <div className="mt-2 p-3 bg-gray-950 border border-gray-800 rounded-xl space-y-3 text-xs">
                    <div className="flex items-center justify-between border-b border-gray-800 pb-2 flex-wrap gap-2">
                      <div>
                        <span className="font-bold text-emerald-400 block">Configure Real Email Sender (SMTP)</span>
                        <div className="flex items-center gap-1.5 mt-1">
                          <button
                            type="button"
                            onClick={() => {
                              setSmtpHost("smtp.gmail.com");
                              setSmtpPort(587);
                            }}
                            className="px-2 py-0.5 rounded bg-gray-900 border border-gray-700 hover:border-emerald-500 text-[11px] text-gray-200"
                          >
                            📧 Gmail Preset
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSmtpHost("smtp.office365.com");
                              setSmtpPort(587);
                            }}
                            className="px-2 py-0.5 rounded bg-gray-900 border border-gray-700 hover:border-blue-500 text-[11px] text-gray-200"
                          >
                            📬 Outlook Preset
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleSaveSmtp("mock")}
                          disabled={savingSmtp}
                          className="px-2 py-1 text-[11px] rounded bg-gray-800 hover:bg-gray-700 text-gray-300"
                        >
                          Use Mock
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveSmtp("smtp")}
                          disabled={savingSmtp || !smtpHost || !smtpUsername}
                          className="px-3 py-1 text-[11px] font-bold rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white"
                        >
                          {savingSmtp ? "Saving..." : "Save & Use Real SMTP"}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-gray-400 block mb-1">
                          SMTP Host <span className="text-emerald-400 font-mono">(use "smtp.gmail.com")</span>
                        </label>
                        <input
                          type="text"
                          value={smtpHost}
                          onChange={(e) => {
                            let val = e.target.value;
                            if (val.includes("@") || val.toLowerCase().endsWith(".gmail.com") || val.toLowerCase() === "gmail.com") {
                              val = "smtp.gmail.com";
                            }
                            setSmtpHost(val);
                          }}
                          placeholder="smtp.gmail.com"
                          className="w-full bg-gray-900 border border-gray-700 rounded p-1.5 text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-400 block mb-1">Port</label>
                        <input
                          type="number"
                          value={smtpPort}
                          onChange={(e) => setSmtpPort(Number(e.target.value))}
                          placeholder="587"
                          className="w-full bg-gray-900 border border-gray-700 rounded p-1.5 text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-400 block mb-1">Your Email (Username)</label>
                        <input
                          type="text"
                          value={smtpUsername}
                          onChange={(e) => setSmtpUsername(e.target.value)}
                          placeholder="your.email@gmail.com"
                          className="w-full bg-gray-900 border border-gray-700 rounded p-1.5 text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-400 block mb-1">Password / Gmail App Password</label>
                        <input
                          type="password"
                          value={smtpPassword}
                          onChange={(e) => setSmtpPassword(e.target.value)}
                          placeholder="16-character App Password"
                          className="w-full bg-gray-900 border border-gray-700 rounded p-1.5 text-white"
                        />
                      </div>
                    </div>
                    <p className="text-[10px] text-gray-400">
                      💡 For Gmail: Use <code className="text-emerald-400">smtp.gmail.com</code> port <code className="text-emerald-400">587</code> with a 16-character App Password from Google Account Security.
                    </p>
                    {smtpStatusMessage && (
                      <div className="p-2 rounded bg-gray-900 text-xs border border-gray-700">
                        {smtpStatusMessage}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Recipient summary cards */}
              <div className="grid grid-cols-3 gap-2">
                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-gray-400 text-[11px] block">Recipients</span>
                  <span className="text-base font-bold text-white flex items-center justify-center gap-1">
                    <Users className="w-3.5 h-3.5 text-emerald-400" />
                    {draft.recipient_count}
                  </span>
                </div>

                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-gray-400 text-[11px] block">Excluded</span>
                  <span className="text-base font-bold text-amber-400">
                    {draft.excluded_count}
                  </span>
                </div>

                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-gray-400 text-[11px] block">Security Hash</span>
                  <span className="text-[10px] font-mono text-gray-400 truncate block" title={draft.content_hash}>
                    {draft.content_hash.slice(0, 8)}...
                  </span>
                </div>
              </div>

              {/* Editable Subject & Body */}
              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-300">Email Content</span>
                  {!isEditing ? (
                    <button
                      onClick={() => setIsEditing(true)}
                      className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 text-[11px]"
                    >
                      <Edit3 className="w-3 h-3" /> Edit Draft
                    </button>
                  ) : (
                    <button
                      onClick={handleSaveEdits}
                      className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 text-[11px] font-bold"
                    >
                      <Check className="w-3 h-3" /> Save Changes
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] text-gray-400">Subject Line</label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                    />
                  ) : (
                    <div className="font-medium text-gray-200 bg-gray-900/60 p-2 rounded-lg border border-gray-800">
                      {draft.subject}
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] text-gray-400">Message Body Template</label>
                  {isEditing ? (
                    <textarea
                      rows={5}
                      value={bodyTemplate}
                      onChange={(e) => setBodyTemplate(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white resize-none"
                    />
                  ) : (
                    <div className="text-gray-300 bg-gray-900/60 p-2.5 rounded-lg border border-gray-800 whitespace-pre-wrap leading-relaxed max-h-36 overflow-y-auto">
                      {draft.body_template}
                    </div>
                  )}
                </div>
              </div>

              {/* Sample Personalization Preview */}
              {draft.sample_preview && (
                <div className="p-3 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-1.5">
                  <span className="text-[11px] font-semibold text-emerald-400 block">
                    Sample Personalized Email (for {draft.sample_preview.recipient.name} &lt;{draft.sample_preview.recipient.email}&gt;)
                  </span>
                  <div className="p-2.5 bg-gray-900/90 border border-gray-800 rounded-lg text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {draft.sample_preview.rendered_body}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer Actions */}
        {draft && !batchResults && (
          <div className="p-4 border-t border-gray-800 bg-gray-950/60 flex items-center justify-between">
            <div className="text-[11px] text-gray-500">
              {isAdmin ? (
                <span className="text-purple-400 font-medium">Logged in as Administrator</span>
              ) : (
                <span className="text-amber-400 font-medium">Student Role: Approval Disabled</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {!isApproved ? (
                <button
                  onClick={handleApprove}
                  disabled={!isAdmin || approving}
                  className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:hover:bg-purple-600 text-white font-semibold text-xs flex items-center gap-2 transition"
                >
                  {approving ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ShieldCheck className="w-3.5 h-3.5" />
                  )}
                  <span>Approve Broadcast as Admin</span>
                </button>
              ) : (
                <button
                  onClick={handleDispatch}
                  disabled={!isAdmin || dispatching}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-semibold text-xs flex items-center gap-2 transition"
                >
                  {dispatching ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Sending {draft.recipient_count} Emails...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Dispatch Broadcast Now ({draft.recipient_count})</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
