"use client";

import { useEffect, useState } from "react";
import { Bot, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Étapes affichées pendant l'attente. L'API ne renvoie pas de progression
 * réelle : on simule la progression avec des délais, la dernière étape reste
 * active jusqu'à l'arrivée de la réponse (jusqu'à ~30 s avec Azure SQL
 * Serverless).
 */
const STEPS = [
  { label: "Connexion SQL", hint: "Réveil d'Azure SQL Serverless…", delay: 0 },
  { label: "Génération SQL", hint: "Traduction de la question en requête…", delay: 6000 },
  { label: "Vérification Sécurité", hint: "Validation de la requête (lecture seule)…", delay: 13000 },
  { label: "Exécution & Analyse", hint: "Interprétation des résultats…", delay: 19000 },
];

export default function AgentStatus() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timers = STEPS.map((step, i) =>
      setTimeout(() => setActiveIndex(i), step.delay)
    );
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => {
      timers.forEach(clearTimeout);
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex w-full gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-blue-600 text-white shadow-lg">
        <Bot className="h-4 w-4" />
      </div>

      <div className="w-full max-w-sm rounded-2xl border border-white/20 bg-white/40 p-4 shadow-lg backdrop-blur-xl dark:bg-black/40">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-semibold tracking-tight">
            L&apos;agent travaille…
          </span>
          <span className="font-mono text-xs tabular-nums opacity-60">
            {elapsed}s
          </span>
        </div>

        <ul className="space-y-2.5">
          {STEPS.map((step, i) => {
            const done = i < activeIndex;
            const active = i === activeIndex;
            return (
              <li
                key={step.label}
                className={cn(
                  "flex items-start gap-3 transition-opacity duration-300",
                  !done && !active && "opacity-35"
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                    done && "bg-emerald-500 text-white",
                    active && "bg-violet-500/20 text-violet-500",
                    !done && !active && "bg-slate-500/20"
                  )}
                >
                  {done ? (
                    <Check className="h-3 w-3" />
                  ) : active ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : null}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight">
                    {step.label}
                  </p>
                  {active && (
                    <p className="mt-0.5 text-xs leading-relaxed opacity-60">
                      {step.hint}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}