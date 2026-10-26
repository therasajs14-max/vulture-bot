"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Square, Paperclip, X, FileText, Mic, MicOff, Volume2 } from "lucide-react";

interface ChatComposerProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  onOpenFileUpload: () => void;
  attachedFile?: { name: string; id: string } | null;
  onRemoveAttachment?: () => void;
  placeholder?: string;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  onStop,
  isStreaming,
  onOpenFileUpload,
  attachedFile,
  onRemoveAttachment,
  placeholder = "Message Vulture Bot or speak into the microphone...",
}) => {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = (event: any) => {
          const transcript = event.results[0]?.[0]?.transcript || "";
          if (transcript) {
            setInput((prev) => {
              const base = prev.trim();
              return base ? `${base} ${transcript.trim()}` : transcript.trim();
            });
          }
        };

        recognition.onerror = (err: any) => {
          console.warn("Speech recognition error:", err);
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      }
    }
  }, []);

  const toggleListening = () => {
    if (!speechSupported) {
      alert("Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.");
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch {
        // ignore
      }
      setIsListening(false);
    } else {
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (e) {
        console.error("Speech recognition start failed:", e);
      }
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!input.trim() || isStreaming) return;
    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch {}
      setIsListening(false);
    }
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  return (
    <div className="p-4 border-t border-gray-800 bg-gray-950/80 backdrop-blur-md">
      <div className="max-w-4xl mx-auto space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Attachment Chip */}
          {attachedFile && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900 border border-emerald-500/40 text-xs text-gray-200 w-fit">
              <FileText className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-medium truncate max-w-xs">{attachedFile.name}</span>
              <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                Ready
              </span>
              {onRemoveAttachment && (
                <button
                  onClick={onRemoveAttachment}
                  className="p-0.5 hover:text-rose-400 text-gray-400 transition"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* Listening Indicator Chip */}
          {isListening && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-950/80 border border-rose-600/60 text-xs text-rose-200 animate-pulse w-fit">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
              <span className="font-semibold">🎙️ Microphone Active: Speak now...</span>
              <button
                type="button"
                onClick={toggleListening}
                className="text-[10px] bg-rose-800/80 px-1.5 py-0.5 rounded hover:bg-rose-700 text-white ml-1 font-bold"
              >
                Stop
              </button>
            </div>
          )}
        </div>

        {/* Composer box */}
        <div className={`flex items-center gap-2 bg-gray-900 border rounded-2xl px-3 py-2 shadow-xl transition-colors ${
          isListening ? "border-rose-500/80 ring-2 ring-rose-500/20" : "border-gray-700/80 focus-within:border-emerald-500/80"
        }`}>
          <button
            type="button"
            onClick={onOpenFileUpload}
            className="p-2 text-gray-400 hover:text-emerald-400 rounded-xl hover:bg-gray-800 transition flex-shrink-0"
            title="Attach Student File (CSV, Excel, PDF)"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening... Speak your message now" : placeholder}
            className="flex-1 bg-transparent border-0 text-sm text-gray-100 placeholder-gray-400 focus:outline-none resize-none py-2 px-1 min-h-[38px] max-h-44 leading-relaxed"
          />

          {/* Microphone Voice Button */}
          <button
            type="button"
            onClick={toggleListening}
            className={`p-2.5 rounded-xl shadow transition flex-shrink-0 ${
              isListening
                ? "bg-rose-600 hover:bg-rose-500 text-white animate-pulse ring-2 ring-rose-400/50"
                : "bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-emerald-400"
            }`}
            title={isListening ? "Stop Microphone" : "Voice Input (Microphone)"}
          >
            {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>

          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="p-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl shadow transition flex-shrink-0"
              title="Stop Generation"
            >
              <Square className="w-4 h-4 fill-white" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="p-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-30 disabled:hover:bg-emerald-600 text-white rounded-xl shadow transition flex-shrink-0"
              title="Send Message"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="text-[11px] text-gray-500 text-center flex items-center justify-center gap-3">
          <span>Click 🎙️ to talk or press <strong>Enter</strong> to send</span>
          <span>•</span>
          <span className="text-emerald-500/80 font-medium">All email dispatches require explicit Admin Approval</span>
        </div>
      </div>
    </div>
  );
};
