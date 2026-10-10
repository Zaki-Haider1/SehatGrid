"use client";
import { useEffect, useRef, useState } from "react";
export const DEMO_PASSWORD = "demo";
const hospitals = ["Shifa International", "PIMS", "Polyclinic", "Kulsum International", "Maroof International", "Ali Medical Centre", "Capital Hospital (CDA)", "NORI"];
export function DemoCredentials({ choose, floating = false }: { choose?: (username: string) => void; floating?: boolean }) {
  const [role, setRole] = useState("planner"), [hospital, setHospital] = useState("8"), [notice, setNotice] = useState("");
  const menu = useRef<HTMLDetailsElement>(null);
  const username = role === "planner" ? "planner" : `${role}-p${hospital.padStart(2, "0")}`;
  useEffect(() => {
    if (!floating) return;
    function outside(event: PointerEvent) { if (event.target instanceof Node && !menu.current?.contains(event.target) && menu.current) menu.current.open = false; }
    function escape(event: KeyboardEvent) { if (event.key === "Escape" && menu.current) menu.current.open = false; }
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, [floating]);
  async function copy() {
    try { await navigator.clipboard.writeText(`Username: ${username}\nPassword: ${DEMO_PASSWORD}`); setNotice("Credentials copied."); }
    catch { setNotice("Select the credentials below to copy manually."); }
  }
  return <details ref={menu} className={`demo-credentials compact-credentials${floating ? " login-demo-access" : ""}`}>
    <summary><span className="demo-access-label">Demo access</span><span className="demo-access-tag">For judges</span><span className="demo-access-chevron" aria-hidden="true">⌄</span></summary>
    <div className="demo-credentials-body">
      <div className="demo-access-heading"><strong>Choose your workspace</strong><small>Synthetic demo accounts only</small></div>
      <label>Role<select value={role} onChange={e => { setRole(e.target.value); setNotice(""); }}><option value="planner">Government planner</option><option value="operator">Hospital reception</option><option value="onboarder">Hospital onboarding</option></select></label>
      {role !== "planner" && <label>Hospital<select value={hospital} onChange={e => { setHospital(e.target.value); setNotice(""); }}>{hospitals.map((name, i) => <option key={name} value={String(i + 1)}>{name} · P{String(i + 1).padStart(2, "0")}</option>)}</select></label>}
      <div className="demo-shared-credentials"><div><small>Username</small><code>{username}</code></div><div><small>Password · all accounts</small><code>{DEMO_PASSWORD}</code></div></div>
      <div className="credential-actions"><button type="button" onClick={() => void copy()}>Copy credentials</button>{choose && <button type="button" className="primary" onClick={() => { choose(username); if (menu.current) menu.current.open = false; }}>Use account →</button>}</div>
      {notice && <small className="copy-notice" role="status">{notice}</small>}
      <a href="/guide">First visit? Follow the demo guide →</a>
    </div>
  </details>;
}
