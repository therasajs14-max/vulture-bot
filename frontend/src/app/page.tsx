"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { UserProfile, ConversationSummary, MessageItem } from "@/lib/types";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatComposer } from "@/components/ChatComposer";
import { FileUploadModal } from "@/components/FileUploadModal";
import { DraftApprovalModal } from "@/components/DraftApprovalModal";
import { SettingsModal } from "@/components/SettingsModal";
import {
  Sparkles,
  FileSpreadsheet,
  MailCheck,
  Send,
  Bot,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";

export default function ChatPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [stopStreamFn, setStopStreamFn] = useState<(() => void) | null>(null);

  // Active AI settings
  const [activeProvider, setActiveProvider] = useState("ollama");
  const [activeModel, setActiveModel] = useState("mistral:latest");
  const [isAiReady, setIsAiReady] = useState(true);

  // Modals state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [approvalDraftId, setApprovalDraftId] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<{ name: string; id: string } | null>(null);
  const [importedDatasetId, setImportedDatasetId] = useState<string | null>(null);
  const [draggedFile, setDraggedFile] = useState<File | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleGlobalDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleGlobalDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setDraggedFile(e.dataTransfer.files[0]);
      setUploadOpen(true);
    }
  };

  useEffect(() => {
    initApp();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const initApp = async () => {
    try {
      // 1. Authenticate user (demo login for instant local access)
      let profile: UserProfile | null = null;
      try {
        profile = await api.getMe();
      } catch {
        const loginRes = await api.demoLogin("admin@vulture.local", "Administrator", true);
        profile = await api.getMe();
      }
      setUser(profile);

      // 2. Load conversations
      const convList = await api.listConversations();
      setConversations(convList);

      if (convList.length > 0) {
        selectConversation(convList[0].id);
      } else {
        await handleNewConversation();
      }

      // 3. Check AI Provider status
      const ai = await api.getAiStatus();
      setIsAiReady(ai.is_ready);
      if (ai.active_provider) {
        setActiveProvider(ai.active_provider);
      }
    } catch (err) {
      console.error("Initialization error:", err);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation("New Conversation");
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setAttachedFile(null);
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  const selectConversation = async (id: string) => {
    setActiveConvId(id);
    try {
      const conv = await api.getConversation(id);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error("Failed to load conversation:", err);
    }
  };

  const handleToggleRole = async () => {
    if (!user) return;
    const newAdmin = !user.is_admin;
    await api.demoLogin(
      newAdmin ? "admin@vulture.local" : "student@vulture.local",
      newAdmin ? "Administrator" : "Student User",
      newAdmin
    );
    const updated = await api.getMe();
    setUser(updated);
  };

  const handleSwitchUserRole = async (isAdmin: boolean) => {
    await api.demoLogin(
      isAdmin ? "admin@vulture.local" : "student@vulture.local",
      isAdmin ? "Administrator" : "Student User",
      isAdmin
    );
    const updated = await api.getMe();
    setUser(updated);
  };

  const handleSelectModel = (provider: string, model: string) => {
    setActiveProvider(provider);
    setActiveModel(model);
  };

  const handleDeleteConversation = async (id: string) => {
    await api.deleteConversation(id);
    const remaining = conversations.filter((c) => c.id !== id);
    setConversations(remaining);
    if (activeConvId === id) {
      if (remaining.length > 0) {
        selectConversation(remaining[0].id);
      } else {
        handleNewConversation();
      }
    }
  };

  const handleRenameConversation = async (id: string, newTitle: string) => {
    await api.updateConversation(id, { title: newTitle });
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
    );
  };

  const handleDatasetImported = (datasetId: string, filename: string) => {
    setImportedDatasetId(datasetId);
    setAttachedFile({ name: filename, id: datasetId });
    // Add system notification to chat
    const sysMsg: MessageItem = {
      id: "sys-" + Date.now(),
      role: "assistant",
      content: `📁 **Dataset Attached: ${filename}**\n\nI have parsed and imported the student records into persistent storage. You can now ask questions like:\n- *"Show all final-year AI & DS students"*\n- *"Find students with missing email addresses"*\n- *"Draft a project review announcement for final-year students"*`,
    };
    setMessages((prev) => [...prev, sysMsg]);
  };

  const handleSendMessage = async (userPrompt: string) => {
    if (!activeConvId) return;

    // Append user message immediately
    const userMsg: MessageItem = {
      id: "u-" + Date.now(),
      role: "user",
      content: userPrompt,
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    // Placeholder for streaming assistant response
    const assistantMsgId = "a-" + Date.now();
    const assistantMsg: MessageItem = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
    };
    setMessages((prev) => [...prev, assistantMsg]);

    // Check if the user is asking to create an email / draft / announcement
    const lower = userPrompt.toLowerCase();
    const isEmailTask =
      (lower.includes("email") ||
        lower.includes("send") ||
        lower.includes("announcement") ||
        lower.includes("reminder") ||
        lower.includes("task")) &&
      (lower.includes("student") || lower.includes("project") || lower.includes("review") || importedDatasetId);

    // Call SSE streaming API
    let fullResponse = "";
    const stopFn = api.streamChat(
      activeConvId,
      userPrompt,
      (chunk) => {
        fullResponse += chunk;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: fullResponse } : m
          )
        );
      },
      (error) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: `Error: ${error}`, is_error: true }
              : m
          )
        );
        setIsStreaming(false);
      },
      async () => {
        setIsStreaming(false);
        // Refresh conversations to update title if changed
        const convList = await api.listConversations();
        setConversations(convList);

        // If user asked to prepare/send an email task, auto-create a draft and show review action button
        if (isEmailTask) {
          try {
            const hasTaskMention =
              lower.includes("task") ||
              lower.includes("assignment") ||
              lower.includes("work") ||
              lower.includes("topic") ||
              lower.includes("project");

            const taskName = hasTaskMention ? "Student Task Assignment" : "Student Announcement / Task";
            const subject = hasTaskMention
              ? "Your Assigned Task & Project Guidelines"
              : "Important Guidelines & Next Steps";
            const bodyTemplate = hasTaskMention
              ? "Dear {name},\n\nHere is your assigned task:\n\n📌 {task}\n\nDepartment: {department}\nAcademic Year: {year}\nRegister Number: {register_number}\n\nPlease complete your assignment and submit your deliverables according to guidelines.\n\nBest regards,\nDepartment Coordinator"
              : "Dear {name},\n\nPlease review your assigned deliverables and prepare your project submission according to guidelines.\n\nDepartment: {department}\nAcademic Year: {year}\nRegister Number: {register_number}\n\nRegards,\nDepartment Coordinator";

            const draftRes = await api.createDraft({
              task_name: taskName,
              subject: subject,
              body_template: bodyTemplate,
              dataset_id: importedDatasetId || undefined,
              conversation_id: activeConvId,
              is_personalized: true,
              selection_description: userPrompt,
            });

            // Append actionable approval card in chat
            const actionMsg: MessageItem = {
              id: "action-" + Date.now(),
              role: "assistant",
              content: `🛡️ **Email Broadcast Draft Created**\n\nI have generated the email draft with personalized tasks for each student. Each recipient will receive their own specific task from your Excel sheet.\n\nAs per security requirements, **mandatory administrator approval** is enforced before any email can be dispatched.\n\nClick the button below to review individual student personalizations, switch to Real Email (SMTP) or Simulation, and authorize dispatch.`,
            };
            setMessages((prev) => [...prev, actionMsg]);
            setApprovalDraftId(draftRes.draft.draft_id);
          } catch (e) {
            console.error("Draft generation error:", e);
          }
        }
      },
      activeProvider,
      activeModel
    );

    setStopStreamFn(() => stopFn);
  };

  const handleStopStreaming = () => {
    if (stopStreamFn) {
      stopStreamFn();
      setIsStreaming(false);
    }
  };

  return (
    <div
      onDragOver={handleGlobalDragOver}
      onDragEnter={handleGlobalDragOver}
      onDrop={handleGlobalDrop}
      className="flex h-screen w-screen overflow-hidden bg-gray-950 text-gray-100"
    >
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConvId}
        onSelectConversation={selectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        onOpenUpload={() => {
          setDraggedFile(null);
          setUploadOpen(true);
        }}
        onOpenApprovalQueue={() => {
          if (approvalDraftId) {
            setApprovalDraftId(approvalDraftId);
          } else {
            alert("No pending draft. Ask Vulture Bot to prepare an email announcement to create one!");
          }
        }}
        pendingApprovalsCount={approvalDraftId ? 1 : 0}
      />

      {/* Main chat column */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <Header
          user={user}
          onOpenSettings={() => setSettingsOpen(true)}
          onToggleRole={handleToggleRole}
          activeProvider={activeProvider}
          activeModel={activeModel}
          onSelectModel={handleSelectModel}
          isAiReady={isAiReady}
        />

        {/* Message area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            /* Empty state / Welcome Hero */
            <div className="max-w-3xl mx-auto px-6 py-16 text-center space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-3xl mx-auto shadow-xl">
                🦅
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl font-bold tracking-tight text-white">
                  Welcome to Vulture Bot
                </h2>
                <p className="text-sm text-gray-400 max-w-lg mx-auto">
                  Production-ready AI assistant with file intelligence, student data analysis, and server-enforced admin approval for email broadcasts.
                </p>
              </div>

              {/* Quick suggestion cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-xl mx-auto pt-2">
                <button
                  onClick={() => {
                    setDraggedFile(null);
                    setUploadOpen(true);
                  }}
                  className="p-3.5 rounded-xl bg-gray-900/80 hover:bg-gray-800/90 border border-gray-800 hover:border-emerald-500/40 transition text-left group"
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 mb-1">
                    <FileSpreadsheet className="w-4 h-4" />
                    <span>Upload Student Records</span>
                  </div>
                  <p className="text-[11px] text-gray-400">
                    Upload CSV or Excel dataset with student names, registers, departments & emails.
                  </p>
                </button>

                <button
                  onClick={() =>
                    handleSendMessage(
                      "Draft a project review task for final-year students. Explain objectives and submission deadlines."
                    )
                  }
                  className="p-3.5 rounded-xl bg-gray-900/80 hover:bg-gray-800/90 border border-gray-800 hover:border-purple-500/40 transition text-left group"
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-purple-400 mb-1">
                    <MailCheck className="w-4 h-4" />
                    <span>Admin-Approved Email Task</span>
                  </div>
                  <p className="text-[11px] text-gray-400">
                    Prepare a personalized task email for final-year students with approval review.
                  </p>
                </button>
              </div>
            </div>
          ) : (
            /* Messages list */
            <div className="max-w-4xl mx-auto divide-y divide-gray-900">
              {messages.map((m) => (
                <React.Fragment key={m.id}>
                  <ChatMessage message={m} />
                  {/* Inline Action for Draft Review */}
                  {m.id.startsWith("action-") && approvalDraftId && (
                    <div className="px-6 py-3 bg-purple-950/20 border-b border-purple-900/30 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-purple-300 font-medium">
                        <ShieldAlert className="w-4 h-4 text-purple-400" />
                        <span>Admin Approval Required Before Dispatch</span>
                      </div>
                      <button
                        onClick={() => setApprovalDraftId(approvalDraftId)}
                        className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow transition flex items-center gap-1.5"
                      >
                        <span>Open Review & Approval Panel</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </React.Fragment>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Composer */}
        <ChatComposer
          onSend={handleSendMessage}
          onStop={handleStopStreaming}
          isStreaming={isStreaming}
          onOpenFileUpload={() => {
            setDraggedFile(null);
            setUploadOpen(true);
          }}
          attachedFile={attachedFile}
          onRemoveAttachment={() => {
            setAttachedFile(null);
            setImportedDatasetId(null);
          }}
        />
      </div>

      {/* Modals */}
      <FileUploadModal
        isOpen={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
          setDraggedFile(null);
        }}
        conversationId={activeConvId || undefined}
        onDatasetImported={handleDatasetImported}
        initialFile={draggedFile}
      />

      <DraftApprovalModal
        isOpen={Boolean(approvalDraftId)}
        onClose={() => setApprovalDraftId(null)}
        draftId={approvalDraftId}
        user={user}
        onBatchSent={() => {
          setApprovalDraftId(null);
        }}
      />

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        user={user}
        onSwitchUser={handleSwitchUserRole}
      />
    </div>
  );
}
