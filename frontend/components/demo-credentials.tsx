"use client";
import { useEffect, useRef, useState } from "react";
export const DEMO_PASSWORD = "demo";
const hospitals = [
  { name: "Shifa International Hospital", slug: "shifa-international", sector: "Private" },
  { name: "Pakistan Institute of Medical Sciences (PIMS)", slug: "pims", sector: "Public" },
  { name: "Federal Government Polyclinic", slug: "polyclinic", sector: "Public" },
  { name: "Kulsum International Hospital", slug: "kulsum-international", sector: "Private" },
  { name: "Maroof International Hospital", slug: "maroof-international", sector: "Private" },
  { name: "Ali Medical Centre", slug: "ali-medical-centre", sector: "Private" },
  { name: "Capital Hospital (CDA)", slug: "capital-hospital", sector: "Public" },
  { name: "NORI Atomic Energy Cancer Hospital", slug: "nori", sector: "Public" },
];
export function DemoCredentials({ choose, floating = false }: { choose?: (username: string) => void; floating?: boolean }) {
  const [role, setRole] = useState("planner"), [hospital, setHospital] = useState("nori"), [sector, setSector] = useState("Public"), [notice, setNotice] = useState("");
  const menu = useRef<HTMLDetailsElement>(null);
  const username = role === "planner" ? "planner" : `${role}-${hospital}`;
  useEffect(() => {
    if (!floating) return;
    function outside(event: PointerEvent) { if (event.target instanceof Node && !menu.current?.contains(event.target) && menu.current) menu.current.open = false; }
    function escape(event: KeyboardEvent) { if (event.key === "Escape" && menu.current) menu.current.open = false; }
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, [floating]);
  async function copy(field?: "username" | "password") {
    const value = field === "username" ? username : field === "password" ? DEMO_PASSWORD : `Username: ${username}\nPassword: ${DEMO_PASSWORD}`;
    try { await navigator.clipboard.writeText(value); setNotice(field === "username" ? "Username copied." : field === "password" ? "Password copied." : "Credentials copied."); }
    catch { setNotice("Select the credentials below to copy manually."); }
  }
  return <details ref={menu} className={`demo-credentials compact-credentials${floating ? " login-demo-access" : ""}`}>
    <summary><span className="demo-access-label">Demo access</span><span className="demo-access-tag">For judges</span><span className="demo-access-chevron" aria-hidden="true">⌄</span></summary>
    <div className="demo-credentials-body">
      <div className="demo-access-heading"><strong>Choose your workspace</strong><small>Synthetic demo accounts only</small></div>
      <label>Role<select value={role} onChange={e => { setRole(e.target.value); setNotice(""); }}><option value="planner">Government planner</option><option value="operator">Hospital reception</option><option value="onboarder">Hospital onboarding</option></select></label>
      {role !== "planner" && <>
        <label>Hospital sector<select value={sector} onChange={e => { const next = e.target.value; setSector(next); setHospital(hospitals.find(h => h.sector === next)!.slug); setNotice(""); }}><option value="Public">Public sector hospitals</option><option value="Private">Private sector hospitals</option></select></label>
        <label>Hospital<select value={hospital} onChange={e => { setHospital(e.target.value); setNotice(""); }}>{hospitals.filter(h => h.sector === sector).map(h => <option key={h.slug} value={h.slug}>{h.name}</option>)}</select></label>
      </>}
      <div className="demo-shared-credentials"><div><small>Username</small><code>{username}</code><button type="button" onClick={() => void copy("username")}>Copy username</button></div><div><small>Password · all accounts</small><code>{DEMO_PASSWORD}</code><button type="button" onClick={() => void copy("password")}>Copy password</button></div></div>
      <div className="credential-actions"><button type="button" onClick={() => void copy()}>Copy credentials</button>{choose && <button type="button" className="primary" onClick={() => { choose(username); if (menu.current) menu.current.open = false; }}>Use account →</button>}</div>
      {notice && <small className="copy-notice" role="status">{notice}</small>}
      <a href="/guide">First visit? Follow the demo guide →</a>
    </div>
  </details>;
}
