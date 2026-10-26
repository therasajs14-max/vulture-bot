"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageItem } from "@/lib/types";
import { Copy, Check, RotateCw, AlertCircle, Bot, User, Volume2, VolumeX } from "lucide-react";

interface ChatMessageProps {
  message: MessageItem;
  onRegenerate?: () => void;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onRegenerate,
  isStreaming = false,
}) => {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleSpeak = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      window.speechSynthesis.cancel();
      // Strip markdown symbols for clean audio speech
      const cleanText = message.content.replace(/[*#_`~>\[\]\(\)]/g, " ");
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      setIsSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div
      className={`py-4 px-4 md:px-6 flex gap-4 transition-colors ${
        isUser ? "bg-transparent" : "bg-gray-900/40 border-y border-gray-800/40"
      }`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-lg bg-emerald-600/30 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center text-emerald-300 font-bold">
            🦅
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">
            {isUser ? "You" : "Vulture Bot"}
          </span>
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-1">
              <button
                onClick={toggleSpeak}
                className={`p-1 rounded transition ${
                  isSpeaking ? "text-emerald-400 bg-emerald-500/20 animate-pulse" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                }`}
                title={isSpeaking ? "Stop Speaking" : "Read aloud (Voice)"}
              >
                {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={handleCopy}
                className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition"
                title="Copy response"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition"
                  title="Regenerate"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
        </div>

        {message.is_error ? (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{message.content}</span>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-gray-200 leading-relaxed text-sm break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
};
