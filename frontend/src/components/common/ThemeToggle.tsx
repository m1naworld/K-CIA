"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type ThemeMode = "light" | "dark";

function resolveInitialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>("dark");

  useEffect(() => {
    setTheme(resolveInitialTheme());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("theme", theme);
    window.dispatchEvent(new CustomEvent("theme-change", { detail: theme }));
  }, [theme]);

  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(nextTheme)}
      className="h-8 border-slate-200 bg-white text-xs text-slate-700 hover:bg-slate-100 dark:border-white/10 dark:bg-gray-900 dark:text-white/70 dark:hover:bg-white/10"
    >
      {theme === "dark" ? "라이트 모드" : "다크 모드"}
    </Button>
  );
}
