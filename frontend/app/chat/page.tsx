"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatComposer } from "@/components/ChatComposer";
import { ChatEmptyState } from "@/components/ChatEmptyState";
import { ChatSidebar } from "@/components/ChatSidebar";
import { ChatTurn } from "@/components/ChatTurn";
import { CompassMark } from "@/components/CompassMark";
import { api, ApiError } from "@/lib/api";
import { friendlyLead } from "@/lib/format";
import { chatStore, profileStore, sessionStore } from "@/lib/store";
import type { ChatMessage, StudentProfile } from "@/lib/types";

function welcomeMessage(name: string): ChatMessage {
  return {
    id: "welcome",
    role: "assistant",
    text:
      `Hi ${name.split(" ")[0] || "there"} — tell me a domain, a skill, or an interest, and I'll chart the ` +
      "closest problem statements in the catalogue. You can push back on any answer in plain language.",
    createdAt: new Date().toISOString(),
  };
}

let idCounter = 0;
const nextId = () => `m${Date.now()}_${idCounter++}`;

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [studentId, setStudentId] = useState<number | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const session = sessionStore.get();
      if (!session) {
        router.replace("/login");
        return;
      }

      let studentId = session.studentId;
      let profile = profileStore.get();

      // The demo backend can be reset independently of the browser (e.g. a
      // fresh seed during development), which orphans an old session's
      // student id. Detect that up front and re-create the student from the
      // locally-saved profile instead of failing later, mid-chat.
      try {
        await api.getStudent(studentId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          if (!profile) {
            sessionStore.clear();
            router.replace("/login");
            return;
          }
          try {
            const fresh = await api.saveStudent({ ...profile, id: undefined });
            profileStore.set(fresh);
            sessionStore.set({ studentId: fresh.id, name: fresh.name, email: session.email });
            studentId = fresh.id;
            profile = fresh;
          } catch {
            sessionStore.clear();
            router.replace("/login");
            return;
          }
        }
        // any other error (e.g. backend unreachable) - proceed optimistically;
        // the composer surfaces a clear error the moment a message is sent.
      }

      if (cancelled) return;
      setStudentId(studentId);
      setProfile(profile);
      const saved = chatStore.get(studentId);
      setMessages(saved.length > 0 ? saved : [welcomeMessage(profile?.name ?? session.name)]);
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const persist = useCallback(
    (next: ChatMessage[]) => {
      setMessages(next);
      if (studentId != null) chatStore.set(studentId, next);
    },
    [studentId],
  );

  const send = useCallback(
    async (text: string) => {
      if (studentId == null || busy) return;
      const userMsg: ChatMessage = { id: nextId(), role: "user", text, createdAt: new Date().toISOString() };
      const pendingMsg: ChatMessage = {
        id: nextId(),
        role: "assistant",
        text: "",
        createdAt: new Date().toISOString(),
        pending: true,
      };
      const withPending = [...messages, userMsg, pendingMsg];
      persist(withPending);
      setBusy(true);
      try {
        const res = await api.refine(studentId, text);
        const answer: ChatMessage = {
          id: pendingMsg.id,
          role: "assistant",
          text: friendlyLead(res),
          detail: res.message,
          createdAt: new Date().toISOString(),
          result: res,
        };
        persist([...withPending.slice(0, -1), answer]);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404 && profile) {
          // session outlived the backend record it points to - recover
          // silently and retry this same message once.
          try {
            const fresh = await api.saveStudent({ ...profile, id: undefined });
            profileStore.set(fresh);
            const session = sessionStore.get();
            sessionStore.set({ studentId: fresh.id, name: fresh.name, email: session?.email ?? "" });
            setStudentId(fresh.id);
            setProfile(fresh);
            const res = await api.refine(fresh.id, text);
            const answer: ChatMessage = {
              id: pendingMsg.id,
              role: "assistant",
              text: friendlyLead(res),
              detail: res.message,
              createdAt: new Date().toISOString(),
              result: res,
            };
            setMessages(withPending.slice(0, -1).concat(answer));
            chatStore.set(fresh.id, withPending.slice(0, -1).concat(answer));
            setBusy(false);
            return;
          } catch {
            /* fall through to the generic error bubble below */
          }
        }
        const answer: ChatMessage = {
          id: pendingMsg.id,
          role: "assistant",
          text:
            err instanceof ApiError
              ? err.message
              : "Something went wrong reaching the model. Try again in a moment.",
          createdAt: new Date().toISOString(),
          error: true,
        };
        persist([...withPending.slice(0, -1), answer]);
      } finally {
        setBusy(false);
      }
    },
    [studentId, busy, messages, persist],
  );

  const newChat = () => {
    if (studentId == null) return;
    chatStore.clear(studentId);
    setMessages([welcomeMessage(profile?.name ?? "")]);
  };

  const logout = () => {
    sessionStore.clear();
    router.push("/login");
  };

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-charcoal-text/60">
        <span className="compass-spin mr-2 inline-block text-brass">
          <CompassMark size={16} />
        </span>
        Loading your session…
      </div>
    );
  }

  const onlyWelcome = messages.length === 1 && messages[0].id === "welcome";

  return (
    <div className="flex h-screen">
      <ChatSidebar profile={profile} onNewChat={newChat} onLogout={logout} />

      <div className="flex min-w-0 flex-1 flex-col bg-tint-blue">
        {/* compact top bar, visible where the full sidebar is hidden */}
        <div className="flex items-center justify-between border-b border-hairline bg-parchment-raised px-4 py-2 text-sm lg:hidden">
          <span className="truncate font-medium">{profile?.name ?? "Chat"}</span>
          <div className="flex gap-3">
            <button type="button" onClick={newChat} className="link-teal">
              New chat
            </button>
            <button type="button" onClick={logout} className="text-charcoal-text/60 hover:text-charcoal-text">
              Log out
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-5 px-4 py-6 sm:px-6">
            {onlyWelcome ? (
              <ChatEmptyState name={profile?.name ?? ""} onPick={send} />
            ) : (
              messages.map((m) => <ChatTurn key={m.id} message={m} />)
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <ChatComposer onSend={send} busy={busy} />
      </div>
    </div>
  );
}
