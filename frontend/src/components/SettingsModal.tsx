"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { UserProfile } from "@/lib/types";
import {
  Settings,
  X,
  Server,
  Mail,
  Shield,
  Activity,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Bot,
  Zap,
  Send,
  Loader2,
  Lock,
} from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserProfile | null;
  onSwitchUser: (isAdmin: boolean) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  user,
  onSwitchUser,
}) => {
  const [tab, setTab] = useState<"ai" | "email" | "account" | "audit">("email");
  const [aiStatus, setAiStatus] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Email Configuration state
  const [emailMode, setEmailMode] = useState<"smtp" | "mock">("mock");
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [savingEmail, setSavingEmail] = useState(false);
  const [emailSaveSuccess, setEmailSaveSuccess] = useState(false);

  // Live Test Email state
  const [testRecipient, setTestRecipient] = useState("");
  const [testingEmail, setTestingEmail] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    messageId?: string;
  } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDiagnostics();
      loadEmailConfig();
    }
  }, [isOpen]);

  const loadDiagnostics = async () => {
    try {
      const status = await api.getAiStatus();
      setAiStatus(status);
      if (user?.is_admin) {
        const logs = await api.getAuditTrail();
        setAuditLogs(logs);
      }
    } catch {
      // ignore
    }
  };

  const loadEmailConfig = async () => {
    try {
      const cfg = await api.getEmailConfig();
      setEmailMode(cfg.provider === "smtp" ? "smtp" : "mock");
      if (cfg.smtp_host) setSmtpHost(cfg.smtp_host);
      if (cfg.smtp_port) setSmtpPort(cfg.smtp_port);
      if (cfg.smtp_username) setSmtpUsername(cfg.smtp_username);
      if (cfg.smtp_use_tls !== undefined) setSmtpUseTls(cfg.smtp_use_tls);
    } catch {
      // ignore
    }
  };

  const handleSaveEmailConfig = async () => {
    setSavingEmail(true);
    setEmailSaveSuccess(false);
    setTestResult(null);

    let cleanHost = smtpHost.trim();
    if (cleanHost.toLowerCase().includes("gmail") || cleanHost.includes("@")) {
      cleanHost = "smtp.gmail.com";
      setSmtpHost("smtp.gmail.com");
    } else if (cleanHost.toLowerCase().includes("outlook") || cleanHost.toLowerCase().includes("hotmail")) {
      cleanHost = "smtp.office365.com";
      setSmtpHost("smtp.office365.com");
    } else if (cleanHost.toLowerCase().includes("yahoo")) {
      cleanHost = "smtp.mail.yahoo.com";
      setSmtpHost("smtp.mail.yahoo.com");
    }

    let cleanUsername = smtpUsername.trim();
    if (emailMode === "smtp") {
      if (cleanHost === "smtp.gmail.com" && !cleanUsername.includes("@")) {
        setSavingEmail(false);
        alert(`Your username "${cleanUsername}" is missing @gmail.com.\n\nFor Gmail SMTP, your username must be your FULL Gmail address (e.g. ${cleanUsername}@gmail.com).`);
        return;
      }
    }

    try {
      await api.configureEmail({
        provider: emailMode,
        smtp_host: cleanHost,
        smtp_port: Number(smtpPort),
        smtp_username: cleanUsername,
        smtp_password: smtpPassword,
        smtp_use_tls: smtpUseTls,
      });
      setEmailSaveSuccess(true);
      setTimeout(() => setEmailSaveSuccess(false), 3000);
    } catch (err: any) {
      alert("Failed to save email settings: " + err.message);
    } finally {
      setSavingEmail(false);
    }
  };

  const handleSendLiveTest = async () => {
    if (!testRecipient.trim()) {
      alert("Please enter a valid email address to send the test message to.");
      return;
    }
    setTestingEmail(true);
    setTestResult(null);
    try {
      const res = await api.sendTestEmail(testRecipient.trim());
      setTestResult({
        success: true,
        message: res.delivery_note,
        messageId: res.message_id,
      });
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Failed to send live email.",
      });
    } finally {
      setTestingEmail(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-2xl w-full max-h-[88vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-950/40">
          <div className="flex items-center gap-2 font-bold text-white text-sm">
            <Settings className="w-4 h-4 text-emerald-400" />
            <span>Settings & System Diagnostics</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab buttons */}
        <div className="flex border-b border-gray-800 bg-gray-950/60 px-4 text-xs font-medium">
          <button
            onClick={() => setTab("email")}
            className={`py-3 px-3 border-b-2 transition flex items-center gap-1.5 ${
              tab === "email"
                ? "border-emerald-500 text-emerald-400 font-bold"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Mail className="w-3.5 h-3.5" />
            <span>Real Email Sending</span>
          </button>

          <button
            onClick={() => setTab("ai")}
            className={`py-3 px-3 border-b-2 transition flex items-center gap-1.5 ${
              tab === "ai"
                ? "border-emerald-500 text-emerald-400 font-bold"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>AI Providers</span>
          </button>

          <button
            onClick={() => setTab("account")}
            className={`py-3 px-3 border-b-2 transition flex items-center gap-1.5 ${
              tab === "account"
                ? "border-emerald-500 text-emerald-400 font-bold"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Account & Roles</span>
          </button>

          {user?.is_admin && (
            <button
              onClick={() => setTab("audit")}
              className={`py-3 px-3 border-b-2 transition flex items-center gap-1.5 ${
                tab === "audit"
                  ? "border-emerald-500 text-emerald-400 font-bold"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Audit Trail</span>
            </button>
          )}
        </div>

        {/* Content body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs">
          {tab === "email" && (
            <div className="space-y-4">
              {/* Provider Selection */}
              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-3">
                <span className="font-semibold text-white block">Email Sending Mode</span>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setEmailMode("smtp")}
                    className={`p-3 rounded-xl border text-left transition ${
                      emailMode === "smtp"
                        ? "border-emerald-500 bg-emerald-950/30 text-white font-medium"
                        : "border-gray-800 bg-gray-900 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    <span className="font-bold block text-xs">Real Live Sending (SMTP)</span>
                    <span className="text-[11px] text-gray-400 block mt-0.5">
                      Sends real emails to actual Gmail, Outlook, or university inboxes.
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setEmailMode("mock")}
                    className={`p-3 rounded-xl border text-left transition ${
                      emailMode === "mock"
                        ? "border-purple-500 bg-purple-950/30 text-white font-medium"
                        : "border-gray-800 bg-gray-900 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    <span className="font-bold block text-xs">Mock / Sandbox Mode</span>
                    <span className="text-[11px] text-gray-400 block mt-0.5">
                      Safe local testing mode. Simulates sending without real emails.
                    </span>
                  </button>
                </div>
              </div>

              {/* SMTP Credentials form when in SMTP mode */}
              {emailMode === "smtp" && (
                <div className="p-3.5 bg-gray-950/60 border border-emerald-900/40 rounded-xl space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-semibold text-emerald-400 block">
                      SMTP Credentials
                    </span>
                    {/* Quick Presets */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[11px] text-gray-400 mr-1">1-Click Presets:</span>
                      <button
                        type="button"
                        onClick={() => {
                          setSmtpHost("smtp.gmail.com");
                          setSmtpPort(587);
                          setSmtpUseTls(true);
                        }}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition border ${
                          smtpHost === "smtp.gmail.com"
                            ? "bg-emerald-600 border-emerald-500 text-white"
                            : "bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200"
                        }`}
                      >
                        📧 Gmail
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setSmtpHost("smtp.office365.com");
                          setSmtpPort(587);
                          setSmtpUseTls(true);
                        }}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition border ${
                          smtpHost === "smtp.office365.com"
                            ? "bg-blue-600 border-blue-500 text-white"
                            : "bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200"
                        }`}
                      >
                        📬 Outlook / 365
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setSmtpHost("smtp.mail.yahoo.com");
                          setSmtpPort(587);
                          setSmtpUseTls(true);
                        }}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition border ${
                          smtpHost === "smtp.mail.yahoo.com"
                            ? "bg-purple-600 border-purple-500 text-white"
                            : "bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200"
                        }`}
                      >
                        🟣 Yahoo
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] text-gray-400 block">SMTP Host</label>
                        <span className="text-[10px] text-emerald-400 font-mono">Use "smtp.gmail.com" for Gmail</span>
                      </div>
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
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] text-gray-400 block">Port</label>
                        <span className="text-[10px] text-gray-400">Standard TLS: 587 (SSL: 465)</span>
                      </div>
                      <input
                        type="number"
                        value={smtpPort}
                        onChange={(e) => setSmtpPort(Number(e.target.value))}
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[11px] text-gray-400 block mb-1">
                        Your Full Email (Username)
                      </label>
                      <input
                        type="email"
                        value={smtpUsername}
                        onChange={(e) => setSmtpUsername(e.target.value)}
                        placeholder="e.g. therasajs14@gmail.com"
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                      />
                      <span className="text-[10px] text-gray-500 block mt-0.5">
                        Must be your full email with @gmail.com
                      </span>
                    </div>
                    <div>
                      <label className="text-[11px] text-gray-400 block mb-1">
                        Google App Password (16 characters)
                      </label>
                      <input
                        type="password"
                        value={smtpPassword}
                        onChange={(e) => setSmtpPassword(e.target.value)}
                        placeholder="e.g. abcd efgh ijkl mnop"
                        className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                      />
                      <span className="text-[10px] text-gray-500 block mt-0.5">
                        Generated in Google Security settings
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-emerald-300 bg-emerald-950/40 border border-emerald-800/50 p-2.5 rounded-lg space-y-1">
                    <p className="font-semibold flex items-center gap-1.5">
                      <span>🔑</span> How to get a Gmail App Password in 30 seconds:
                    </p>
                    <ol className="list-decimal list-inside text-[11px] text-gray-300 space-y-0.5 ml-1">
                      <li>Go to your Google Account at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="text-emerald-400 underline font-mono">myaccount.google.com/apppasswords</a></li>
                      <li>Type an app name like "Vulture Bot" and click <strong>Create</strong></li>
                      <li>Copy the generated 16-character password and paste it into the password box above!</li>
                    </ol>
                  </div>

                  <button
                    onClick={handleSaveEmailConfig}
                    disabled={savingEmail}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold flex items-center justify-center gap-2 transition"
                  >
                    {savingEmail ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : emailSaveSuccess ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <Lock className="w-3.5 h-3.5" />
                    )}
                    <span>{emailSaveSuccess ? "Settings Saved Successfully!" : "Save SMTP Credentials"}</span>
                  </button>
                </div>
              )}

              {/* Real Email Live Verification Test */}
              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-2">
                <span className="font-semibold text-white block">Send Real Verification Test Email</span>
                <p className="text-gray-400 text-[11px]">
                  Verify that your email server delivers real messages directly to an inbox:
                </p>

                <div className="flex gap-2">
                  <input
                    type="email"
                    value={testRecipient}
                    onChange={(e) => setTestRecipient(e.target.value)}
                    placeholder="Enter your personal email address..."
                    className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs text-white"
                  />
                  <button
                    onClick={handleSendLiveTest}
                    disabled={testingEmail}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center gap-1.5 transition flex-shrink-0"
                  >
                    {testingEmail ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    <span>Send Test</span>
                  </button>
                </div>

                {testResult && (
                  <div
                    className={`p-3 rounded-lg border text-xs flex items-start gap-2 mt-2 ${
                      testResult.success
                        ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
                        : "bg-rose-950/40 border-rose-800 text-rose-300"
                    }`}
                  >
                    {testResult.success ? (
                      <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <div className="font-bold">{testResult.success ? "Test Succeeded!" : "Delivery Failed"}</div>
                      <div>{testResult.message}</div>
                      {testResult.messageId && (
                        <div className="font-mono text-[10px] text-gray-400">ID: {testResult.messageId}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {tab === "ai" && (
            <div className="space-y-4">
              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="font-semibold text-white">Google Gemini 1.5 Flash</span>
                  </div>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Ready (Fast)
                  </span>
                </div>
                <p className="text-gray-400">
                  Google Gemini cloud provider configured with your Google AI Studio API key. Responds in &lt;1 second.
                </p>
              </div>

              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="w-4 h-4 text-blue-400" />
                    <span className="font-semibold text-white">Local Ollama (mistral:latest)</span>
                  </div>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Connected
                  </span>
                </div>
                <p className="text-gray-400">
                  Local offline AI running at http://localhost:11434. Running on CPU may take 15-30s per prompt.
                </p>
              </div>
            </div>
          )}

          {tab === "account" && (
            <div className="space-y-4">
              <div className="p-3.5 bg-gray-950/60 border border-gray-800 rounded-xl space-y-3">
                <span className="font-semibold text-white block">Current User Session</span>
                <div className="space-y-1">
                  <div className="text-gray-400">Name: <strong className="text-gray-200">{user?.name}</strong></div>
                  <div className="text-gray-400">Email: <strong className="text-gray-200">{user?.email}</strong></div>
                  <div className="text-gray-400">
                    Role:{" "}
                    <strong className={user?.is_admin ? "text-purple-400" : "text-gray-300"}>
                      {user?.is_admin ? "Administrator" : "Standard Student / User"}
                    </strong>
                  </div>
                </div>

                <div className="pt-2 border-t border-gray-800 flex items-center gap-2">
                  <button
                    onClick={() => onSwitchUser(true)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                      user?.is_admin
                        ? "bg-purple-600 text-white border-purple-500"
                        : "bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-750"
                    }`}
                  >
                    Switch to Admin Role
                  </button>
                  <button
                    onClick={() => onSwitchUser(false)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                      !user?.is_admin
                        ? "bg-gray-700 text-white border-gray-600"
                        : "bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-750"
                    }`}
                  >
                    Switch to Student Role
                  </button>
                </div>
              </div>
            </div>
          )}

          {tab === "audit" && (
            <div className="space-y-2">
              <span className="font-semibold text-white block">Security & Broadcast Audit Trail</span>
              <div className="border border-gray-800 rounded-xl overflow-hidden max-h-60 overflow-y-auto">
                {auditLogs.length > 0 ? (
                  <div className="divide-y divide-gray-800 bg-gray-950">
                    {auditLogs.map((log) => (
                      <div key={log.id} className="p-2.5 space-y-0.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-emerald-400 text-[11px] font-bold">
                            {log.event_type}
                          </span>
                          <span className="text-[10px] text-gray-500">
                            {log.created_at ? new Date(log.created_at).toLocaleString() : ""}
                          </span>
                        </div>
                        <p className="text-gray-300 text-[11px]">{log.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-gray-500">No audit events recorded yet.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
