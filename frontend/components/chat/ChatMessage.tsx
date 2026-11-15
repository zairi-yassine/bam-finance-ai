"use client";

import { useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronDown,
  Copy,
  Database,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type ChatRole = "user" | "assistant";

export interface Message {
  id: string;
  role: ChatRole;
  content: string;
  sql?: string;
  isError?: boolean;
}

/* Thème vert sur fond noir pour le SQL */
const sqlTheme: { [key: string]: React.CSSProperties } = {
  'code[class*="language-"]': {
    color: "#4ade80",
    background: "none",
    fontFamily:
      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: "0.85rem",
    lineHeight: 1.7,
    whiteSpace: "pre",
  },
  'pre[class*="language-"]': {
    color: "#4ade80",
    background: "#050505",
    margin: 0,
    padding: "1rem",
    overflow: "auto",
  },
  keyword: { color: "#86efac", fontWeight: 700 },
  function: { color: "#34d399" },
  string: { color: "#bef264" },
  number: { color: "#6ee7b7" },
  operator: { color: "#a7f3d0" },
  punctuation: { color: "#22c55e" },
  comment: { color: "#4b5563", fontStyle: "italic" },
  "class-name": { color: "#86efac" },
  builtin: { color: "#34d399" },
};

function SqlBlock({ code }: { code: string }) {
  return (
    <SyntaxHighlighter
      language="sql"
      style={sqlTheme}
      customStyle={{ background: "#050505", margin: 0 }}
      wrapLongLines
    >
      {code.trim()}
    </SyntaxHighlighter>
  );
}

const markdownComponents: Components = {
  p: ({ children }) => (
    <p className="leading-relaxed mb-3 last:mb-0">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900 dark:text-white">
      {children}
    </strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => (
    <ul className="list-disc pl-5 mb-3 space-y-1.5 marker:text-violet-500">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-5 mb-3 space-y-1.5 marker:text-violet-500">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => (
    <h1 className="text-xl font-bold tracking-tighter mb-3 mt-4">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold tracking-tighter mb-2 mt-4">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold tracking-tight mb-2 mt-3">
      {children}
    </h3>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-violet-600 dark:text-violet-400 underline underline-offset-4"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-violet-500/60 pl-4 italic opacity-80 mb-3">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-xl border border-white/20 bg-white/30 dark:bg-white/5">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-violet-500/10 text-left">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 font-semibold whitespace-nowrap">{children}</th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 border-t border-white/10 whitespace-nowrap">
      {children}
    </td>
  ),
  code: ({ className, children }) => {
    const match = /language-(\w+)/.exec(className || "");
    const text = String(children).replace(/\n$/, "");
    if (match) {
      return (
        <div className="my-3 overflow-hidden rounded-xl border border-white/10">
          <SqlBlock code={text} />
        </div>
      );
    }
    return (
      <code className="rounded-md bg-slate-900/10 dark:bg-white/10 px-1.5 py-0.5 text-[0.85em] font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
};

function SqlAccordion({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard indisponible */
    }
  };

  return (
    <details className="group mt-4 overflow-hidden rounded-xl border border-white/20 bg-black/5 dark:bg-white/5">
      <summary className="flex cursor-pointer select-none list-none items-center gap-2 px-4 py-2.5 text-sm font-medium [&::-webkit-details-marker]:hidden">
        <Database className="h-4 w-4 text-emerald-500" />
        <span>Voir la requête SQL générée</span>
        <button
          type="button"
          onClick={handleCopy}
          className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs opacity-70 transition hover:bg-white/20 hover:opacity-100"
          aria-label="Copier la requête SQL"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? "Copié" : "Copier"}
        </button>
        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
      </summary>
      <SqlBlock code={sql} />
    </details>
  );
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-lg",
          isUser
            ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
            : message.isError
              ? "bg-red-500 text-white"
              : "bg-gradient-to-br from-violet-600 to-blue-600 text-white"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : message.isError ? (
          <AlertTriangle className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>

      {/* Bulle */}
      <div
        className={cn(
          "min-w-0 max-w-[85%] rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-lg backdrop-blur-xl",
          isUser
            ? "border-violet-500/30 bg-gradient-to-br from-violet-600/90 to-blue-600/90 text-white"
            : message.isError
              ? "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300"
              : "border-white/20 bg-white/40 dark:bg-black/40"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>
            {message.sql && <SqlAccordion sql={message.sql} />}
          </>
        )}
      </div>
    </div>
  );
}