"use client";

import React from "react";
import { UserProfile } from "@/lib/types";
import {
  Sparkles,
  Shield,
  User,
  Settings,
  ChevronDown,
  Moon,
  Sun,
  Bot,
  Zap,
} from "lucide-react";

interface HeaderProps {
  user: UserProfile | null;
  onOpenSettings: () => void;
  onToggleRole: () => void;
  activeProvider: string;
  activeModel: string;
  onSelectModel: (provider: string, model: string) => void;
  isAiReady: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  onOpenSettings,
  onToggleRole,
  activeProvider,
  activeModel,
  onSelectModel,
  isAiReady,
}) => {
  const [modelDropdownOpen, setModelDropdownOpen] = React.useState(false);

  return (
    <header className="h-14 border-b border-gray-800 bg-gray-900/60 backdrop-blur-md px-4 flex items-center justify-between z-10 sticky top-0">
      {/* Brand & AI Model indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 font-bold text-white tracking-wide">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            🦅
          </div>
          <span className="hidden sm:inline bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
            Vulture Bot
          </span>
        </div>

        {/* Model Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700 text-gray-200 transition"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isAiReady ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="capitalize">{activeProvider}:</span>
            <span className="font-semibold text-emerald-300">{activeModel}</span>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          </button>

          {modelDropdownOpen && (
            <div className="absolute left-0 mt-2 w-56 rounded-xl bg-gray-900 border border-gray-800 shadow-2xl p-1.5 z-50">
              <div className="text-[11px] font-semibold text-gray-400 px-2.5 py-1 uppercase tracking-wider">
                Select Model
              </div>
              <button
                onClick={() => {
                  onSelectModel("ollama", "mistral:latest");
                  setModelDropdownOpen(false);
                }}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center justify-between hover:bg-gray-800 transition ${
                  activeProvider === "ollama" ? "bg-emerald-950/40 text-emerald-300 font-medium" : "text-gray-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Bot className="w-3.5 h-3.5 text-blue-400" />
                  <span>Ollama: mistral:latest</span>
                </div>
                <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded">Local</span>
              </button>

              <button
                onClick={() => {
                  onSelectModel("gemini", "gemini-1.5-flash");
                  setModelDropdownOpen(false);
                }}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center justify-between hover:bg-gray-800 transition ${
                  activeProvider === "gemini" ? "bg-emerald-950/40 text-emerald-300 font-medium" : "text-gray-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Google Gemini 1.5 Flash</span>
                </div>
                <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">Cloud</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right controls: Role switcher, Settings, Profile */}
      <div className="flex items-center gap-2.5">
        {user && (
          <button
            onClick={onToggleRole}
            title="Click to toggle between Admin and Student role for testing security barriers"
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border transition ${
              user.is_admin
                ? "bg-purple-950/40 border-purple-500/40 text-purple-300 hover:bg-purple-900/50"
                : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-750"
            }`}
          >
            {user.is_admin ? (
              <>
                <Shield className="w-3.5 h-3.5 text-purple-400" />
                <span>Admin Role</span>
              </>
            ) : (
              <>
                <User className="w-3.5 h-3.5 text-gray-400" />
                <span>Student Role</span>
              </>
            )}
          </button>
        )}

        <button
          onClick={onOpenSettings}
          className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
          title="Settings & System Diagnostics"
        >
          <Settings className="w-4 h-4" />
        </button>

        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-gray-800">
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-xs font-bold text-gray-900">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-xs font-medium text-gray-300 hidden md:inline">
              {user.name}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
