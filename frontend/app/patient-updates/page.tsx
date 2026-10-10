"use client";
import { useEffect, useRef, useState } from "react";
import { api, type State } from "@/lib/api";

export default function PatientUpdates() {
  const [messages, setMessages] = useState<NonNullable<State["notifications"]>>(
    [],
  );
  const [recipient, setRecipient] = useState("");
  const [error, setError] = useState("");
  const chat = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let live = true;
    const load = async () => {
      const token = sessionStorage.getItem("sehat-token");
      if (!token) {
        setError("Open this preview from the signed-in reception workspace.");
        return;
      }
      try {
        const state = await api<State>("state", token);
        if (live) {
          setMessages(state.notifications || []);
          setError("");
        }
      } catch {
        if (live)
          setError("Session unavailable. Reopen from the reception workspace.");
      }
    };
    void load();
    const timer = setInterval(load, 5000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);
  const contacts = [...new Set(messages.map((m) => m.request_id))];
  const current = recipient || contacts[0];
  useEffect(() => {
    if (chat.current) chat.current.scrollTop = chat.current.scrollHeight;
  }, [messages.length, current]);
  return (
    <main className="patient-demo">
      <aside>
        <span className="eyebrow">SEHAT GRID · DEMO</span>
        <h1>
          Care updates,
          <br />
          where patients are.
        </h1>
        <p>
          A WhatsApp-style preview of referral updates. Confirm or reroute a
          consented patient in the reception tab and their messages appear here.
        </p>
        <p className="demo-disclosure">
          Simulation only · No messages are sent to WhatsApp.
        </p>
        {contacts.length > 0 && (
          <label>
            Preview patient reference
            <select
              value={current}
              onChange={(e) => setRecipient(e.target.value)}
            >
              {contacts.map((c) => (
                <option key={c} value={c}>
                  {messages.find((m) => m.request_id === c)?.recipient} · {c}
                </option>
              ))}
            </select>
          </label>
        )}
        {error && <p role="alert">{error}</p>}
      </aside>
      <section className="chat-phone" aria-label="Patient message preview">
        <header>
          <span className="chat-avatar">SG</span>
          <div>
            <strong>SEHAT GRID</strong>
            <small>Patient updates · Demo</small>
          </div>
        </header>
        <div className="chat-messages" ref={chat}>
          <span className="chat-date">Referral updates</span>
          {messages
            .filter((m) => m.request_id === current)
            .map((m) => (
              <article className="chat-bubble" key={m.id}>
                <p>{m.message}</p>
                <small>
                  {new Date(m.created_at).toLocaleTimeString("en-PK", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}{" "}
                  · Simulated
                </small>
              </article>
            ))}
          {!messages.length && (
            <article className="chat-bubble">
              <p>
                Your confirmed destination, service and reception instructions
                will appear here after the hospital completes confirmation.
              </p>
              <small>Example placeholder · not a patient message</small>
            </article>
          )}
        </div>
        <footer>Read-only demonstration · WhatsApp is not connected</footer>
      </section>
    </main>
  );
}
