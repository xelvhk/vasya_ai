import React, { useMemo, useState } from "react";
import { Mic, Send, X, MessageCircle, Settings, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type VasyaState = "idle" | "listening" | "thinking" | "speaking" | "error";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
};

const stateLabel: Record<VasyaState, string> = {
  idle: "Готов помочь",
  listening: "Слушаю",
  thinking: "Думаю",
  speaking: "Отвечаю",
  error: "Нужна проверка",
};

const stateHint: Record<VasyaState, string> = {
  idle: "Напиши команду или включи голосовой режим.",
  listening: "Говори — я распознаю команду.",
  thinking: "Разбираю запрос и подбираю действие.",
  speaking: "Озвучиваю ответ.",
  error: "Что-то пошло не так, но это можно починить.",
};

function VasyaAvatar({ state }: { state: VasyaState }) {
  const isActive = state === "listening" || state === "thinking" || state === "speaking";

  return (
    <div className="relative flex h-14 w-14 items-center justify-center">
      {isActive && (
        <>
          <span className="absolute h-14 w-14 animate-ping rounded-full bg-cyan-400/20" />
          <span className="absolute h-16 w-16 rounded-full bg-violet-500/10 blur-md" />
        </>
      )}

      <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-cyan-400 p-[2px] shadow-[0_0_28px_rgba(108,92,231,0.45)]">
        <div className="flex h-full w-full items-center justify-center rounded-full bg-slate-950">
          <svg viewBox="0 0 96 96" className="h-10 w-10" aria-label="Vasya AI avatar" role="img">
            <defs>
              <linearGradient id="vasyaGradient" x1="18" y1="18" x2="78" y2="78">
                <stop offset="0%" stopColor="#8B5CF6" />
                <stop offset="100%" stopColor="#00D4FF" />
              </linearGradient>
            </defs>
            <path
              d="M21 44C22 25 36 15 53 17C69 19 78 30 77 46"
              fill="none"
              stroke="url(#vasyaGradient)"
              strokeWidth="6"
              strokeLinecap="round"
            />
            <path
              d="M31 27C36 15 48 13 56 18C49 18 43 21 38 29C48 20 63 22 70 33"
              fill="none"
              stroke="url(#vasyaGradient)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <rect x="22" y="43" width="22" height="15" rx="6" fill="none" stroke="#E5E7EB" strokeWidth="5" />
            <rect x="52" y="43" width="22" height="15" rx="6" fill="none" stroke="#E5E7EB" strokeWidth="5" />
            <path d="M44 51H52" stroke="#E5E7EB" strokeWidth="5" strokeLinecap="round" />
            <path
              d={state === "error" ? "M36 70C43 64 53 64 60 70" : "M36 68C43 74 53 74 60 68"}
              fill="none"
              stroke="#E5E7EB"
              strokeWidth="5"
              strokeLinecap="round"
            />
            {state === "speaking" && (
              <path d="M80 48C84 53 84 59 80 64" fill="none" stroke="#00D4FF" strokeWidth="4" strokeLinecap="round" />
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}

function VoiceOrb({ state }: { state: VasyaState }) {
  const bars = useMemo(() => [18, 28, 40, 24, 34, 48, 30, 22, 36], []);

  if (state === "speaking") {
    return (
      <div className="flex h-12 items-center justify-center gap-1 rounded-2xl border border-cyan-400/20 bg-cyan-400/5 px-4">
        {bars.map((height, index) => (
          <span
            key={index}
            className="w-1 rounded-full bg-cyan-300/90"
            style={{
              height,
              animation: `vasyaWave 900ms ${index * 80}ms ease-in-out infinite`,
            }}
          />
        ))}
      </div>
    );
  }

  if (state === "thinking") {
    return (
      <div className="flex h-12 items-center justify-center gap-2 rounded-2xl border border-violet-400/20 bg-violet-400/5 px-4">
        {[0, 1, 2].map((item) => (
          <span
            key={item}
            className="h-2.5 w-2.5 rounded-full bg-violet-300"
            style={{ animation: `vasyaDots 1s ${item * 150}ms ease-in-out infinite` }}
          />
        ))}
      </div>
    );
  }

  if (state === "listening") {
    return (
      <div className="relative flex h-12 w-12 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-400/5">
        <span className="absolute h-10 w-10 animate-ping rounded-full bg-cyan-300/20" />
        <Mic className="relative h-5 w-5 text-cyan-200" />
      </div>
    );
  }

  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-900">
      <Sparkles className="h-5 w-5 text-violet-300" />
    </div>
  );
}

export default function VasyaAIWidget() {
  const [open, setOpen] = useState(true);
  const [state, setState] = useState<VasyaState>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      text: "Привет! Я Вася. Могу создать задачу, подсказать по проекту или помочь с кодом.",
    },
  ]);

  function sendMessage() {
    const text = input.trim();
    if (!text) return;

    setMessages((current) => [...current, { id: Date.now(), role: "user", text }]);
    setInput("");
    setState("thinking");

    window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: "Понял. В реальном проекте здесь будет ответ от orchestrator/router Vasya AI.",
        },
      ]);
      setState("speaking");
      window.setTimeout(() => setState("idle"), 1600);
    }, 900);
  }

  function toggleVoice() {
    if (state === "listening") {
      setState("idle");
      return;
    }
    setState("listening");
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(108,92,231,0.24),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(0,212,255,0.16),_transparent_28%),#020617] p-6 text-slate-100">
      <style>{`
        @keyframes vasyaWave {
          0%, 100% { transform: scaleY(0.45); opacity: .55; }
          50% { transform: scaleY(1); opacity: 1; }
        }
        @keyframes vasyaDots {
          0%, 100% { transform: translateY(0); opacity: .45; }
          50% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>

      <div className="mx-auto max-w-4xl pt-10">
        <div className="mb-8">
          <p className="mb-2 text-sm uppercase tracking-[0.25em] text-cyan-200/70">Vasya AI Widget</p>
          <h1 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">Локальный AI-ассистент с характером</h1>
          <p className="mt-4 max-w-2xl text-base text-slate-400">
            Пример виджета: компактный аватар для чата, voice-orb для голосового режима и управляемые состояния.
          </p>
        </div>
      </div>

      <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-4">
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: 18, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 18, scale: 0.96 }}
              transition={{ duration: 0.2 }}
            >
              <Card className="w-[360px] overflow-hidden rounded-3xl border-slate-800 bg-slate-950/92 text-slate-100 shadow-2xl shadow-violet-950/30 backdrop-blur-xl">
                <div className="border-b border-slate-800 bg-slate-900/70 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <VasyaAvatar state={state} />
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="font-semibold text-white">Vasya AI</h2>
                          <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-300">local</span>
                        </div>
                        <p className="text-xs text-slate-400">{stateLabel[state]}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button size="icon" variant="ghost" className="h-8 w-8 rounded-full text-slate-400 hover:bg-slate-800 hover:text-white">
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button onClick={() => setOpen(false)} size="icon" variant="ghost" className="h-8 w-8 rounded-full text-slate-400 hover:bg-slate-800 hover:text-white">
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/80 p-3">
                    <div>
                      <p className="text-sm font-medium text-slate-200">{stateLabel[state]}</p>
                      <p className="text-xs text-slate-500">{stateHint[state]}</p>
                    </div>
                    <VoiceOrb state={state} />
                  </div>
                </div>

                <CardContent className="p-0">
                  <div className="h-[300px] space-y-3 overflow-y-auto px-4 py-4">
                    {messages.map((message) => (
                      <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[82%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                            message.role === "user"
                              ? "bg-gradient-to-br from-violet-500 to-cyan-500 text-white"
                              : "border border-slate-800 bg-slate-900 text-slate-200"
                          }`}
                        >
                          {message.text}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-slate-800 p-3">
                    <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/70 p-2">
                      <Button
                        onClick={toggleVoice}
                        size="icon"
                        className={`h-9 w-9 rounded-xl ${
                          state === "listening"
                            ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                            : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                        }`}
                      >
                        <Mic className="h-4 w-4" />
                      </Button>
                      <input
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") sendMessage();
                        }}
                        placeholder="Напиши команду Васе..."
                        className="min-w-0 flex-1 bg-transparent px-1 text-sm text-slate-100 outline-none placeholder:text-slate-500"
                      />
                      <Button onClick={sendMessage} size="icon" className="h-9 w-9 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 text-white hover:opacity-90">
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {!open && (
          <motion.button
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={() => setOpen(true)}
            className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-cyan-400 shadow-2xl shadow-cyan-950/40"
            aria-label="Open Vasya AI widget"
          >
            <MessageCircle className="h-7 w-7 text-white" />
          </motion.button>
        )}
      </div>
    </div>
  );
}
