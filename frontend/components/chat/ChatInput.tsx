"use client";

import { useRef, useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (question: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !isLoading;

  const submit = () => {
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="w-full">
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border border-white/20 bg-white/40 p-2 shadow-xl backdrop-blur-xl transition",
          "focus-within:border-violet-500/50 focus-within:ring-2 focus-within:ring-violet-500/20",
          "dark:bg-black/40"
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isLoading}
          placeholder="Posez votre question sur les données de Bank Al-Maghrib…"
          className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm leading-relaxed outline-none placeholder:text-slate-500 disabled:opacity-60 dark:placeholder:text-slate-400"
        />
        <Button
          type="button"
          onClick={submit}
          disabled={!canSend}
          className="h-11 shrink-0 gap-2 rounded-xl border-0 bg-gradient-to-r from-violet-600 to-blue-600 px-5 text-white shadow-lg shadow-violet-500/30 transition hover:from-violet-500 hover:to-blue-500 hover:shadow-violet-500/50 disabled:opacity-40"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowUp className="h-4 w-4" />
          )}
          <span className="hidden sm:inline">Envoyer</span>
        </Button>
      </div>
      <p className="mt-2 text-center text-xs text-slate-500 dark:text-slate-400">
        Entrée pour envoyer · Maj + Entrée pour un retour à la ligne
      </p>
    </div>
  );
}