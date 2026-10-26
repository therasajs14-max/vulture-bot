"use client";

import React, { useState } from "react";
import { ConversationSummary } from "@/lib/types";
import {
  Plus,
  MessageSquare,
  Search,
  Trash2,
  Edit2,
  Archive,
  ChevronLeft,
  ChevronRight,
  Upload,
  MailCheck,
  Check,
  X,
} from "lucide-react";

interface SidebarProps {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onOpenUpload: () => void;
  onOpenApprovalQueue: () => void;
  pendingApprovalsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
  onOpenUpload,
  onOpenApprovalQueue,
  pendingApprovalsCount = 0,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const startRename = (conv: ConversationSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveRename = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  return (
    <aside
      className={`h-[calc(100vh-3.5rem)] bg-gray-950/80 border-r border-gray-800 transition-all duration-300 flex flex-col z-20 ${
        collapsed ? "w-16" : "w-72"
      }`}
    >
      {/* Top action row */}
      <div className="p-3 flex items-center justify-between border-b border-gray-800/80">
        {!collapsed && (
          <button
            onClick={onNewConversation}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 transition active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        )}

        {collapsed && (
          <button
            onClick={onNewConversation}
            className="w-10 h-10 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center transition mx-auto"
            title="New Chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 ml-1 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Quick shortcuts: Upload Dataset & Approval Queue */}
      {!collapsed && (
        <div className="px-3 py-2 space-y-1.5 border-b border-gray-800/60">
          <button
            onClick={onOpenUpload}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-gray-900/80 hover:bg-gray-800/90 text-xs font-medium text-gray-300 border border-gray-800 transition group"
          >
            <div className="flex items-center gap-2">
              <Upload className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition" />
              <span>Upload Student File</span>
            </div>
            <span className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">CSV/XLSX</span>
          </button>

          <button
            onClick={onOpenApprovalQueue}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-gray-900/80 hover:bg-gray-800/90 text-xs font-medium text-gray-300 border border-gray-800 transition group"
          >
            <div className="flex items-center gap-2">
              <MailCheck className="w-3.5 h-3.5 text-purple-400 group-hover:scale-110 transition" />
              <span>Admin Email Approval</span>
            </div>
            {pendingApprovalsCount > 0 && (
              <span className="text-[10px] bg-purple-500/30 text-purple-300 font-bold px-1.5 py-0.5 rounded-full">
                {pendingApprovalsCount}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Search box */}
      {!collapsed && (
        <div className="p-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-900/90 border border-gray-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500/60 transition"
            />
          </div>
        </div>
      )}

      {/* Conversation history list */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        {filtered.map((conv) => {
          const isActive = conv.id === activeConversationId;
          const isEditing = editingId === conv.id;

          if (collapsed) {
            return (
              <button
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`w-10 h-10 mx-auto rounded-lg flex items-center justify-center transition ${
                  isActive ? "bg-emerald-600/20 text-emerald-400" : "text-gray-400 hover:bg-gray-800"
                }`}
                title={conv.title}
              >
                <MessageSquare className="w-4 h-4" />
              </button>
            );
          }

          return (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition ${
                isActive
                  ? "bg-gray-800/90 text-white font-medium border border-gray-700/60"
                  : "text-gray-400 hover:bg-gray-900/80 hover:text-gray-200"
              }`}
            >
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-emerald-400" : "text-gray-500"}`} />
                {isEditing ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-gray-950 border border-emerald-500/60 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none flex-1"
                    autoFocus
                  />
                ) : (
                  <span className="truncate">{conv.title}</span>
                )}
              </div>

              {/* Actions on hover */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {isEditing ? (
                  <>
                    <button
                      onClick={(e) => saveRename(conv.id, e)}
                      className="p-1 hover:text-emerald-400 transition"
                      title="Save"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(null);
                      }}
                      className="p-1 hover:text-rose-400 transition"
                      title="Cancel"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={(e) => startRename(conv, e)}
                      className="p-1 text-gray-500 hover:text-gray-300 transition"
                      title="Rename"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="p-1 text-gray-500 hover:text-rose-400 transition"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}

        {!collapsed && filtered.length === 0 && (
          <div className="text-center py-8 text-gray-600 text-xs">
            No conversations found
          </div>
        )}
      </div>
    </aside>
  );
};
