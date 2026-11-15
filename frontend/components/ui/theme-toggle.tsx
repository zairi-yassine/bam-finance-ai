"use client";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      className="rounded-full bg-white/50 dark:bg-black/50 backdrop-blur-md border border-white/20 dark:border-white/10"
    >
      {theme === "light" ? <Moon className="h-5 w-5 text-slate-800" /> : <Sun className="h-5 w-5 text-slate-200" />}
    </Button>
  );
}