"use client";
import { useState } from "react";

export const DEMO_PASSWORD = "isolated-browser-demo-password";
const hospitals = ["Shifa International", "PIMS", "Federal Government Polyclinic", "Kulsum International", "Maroof International", "Ali Medical Centre", "Capital Hospital (CDA)", "NORI"];
const accounts = [
  { username: "planner", label: "Government representative", purpose: "Review demand, approve the resource plan and inspect outcomes." },
  ...hospitals.map((name, i) => ({ username: `operator-p${String(i + 1).padStart(2, "0")}`, label: `${name} · Reception`, purpose: i === 7 ? "Start here to route A-01 or B-01 after the government plan is approved." : [1, 2, 6].includes(i) ? "Public hospital reception: originate and receive eligible referrals." : "Private hospital reception: accept incoming referrals and record care." })),
  ...hospitals.map((name, i) => ({ username: `onboarder-p${String(i + 1).padStart(2, "0")}`, label: `${name} · Onboarding`, purpose: "Manage this hospital's profile, dated quota, services and prices." })),
];

export function DemoCredentials({ choose }: { choose?: (username: string) => void }) {
  const [selected, setSelected] = useState("planner");
  const [notice, setNotice] = useState("");
  const account = accounts.find(a => a.username === selected)!;
  async function copy(value: string, label: string) {
    try { await navigator.clipboard.writeText(value); setNotice(`${label} copied.`); }
    catch { setNotice("Clipboard access is unavailable. Select and copy the displayed text manually."); }
  }
  return <details className="demo-credentials">
    <summary>Demo accounts & passwords <span>For judges</span></summary>
    <div className="demo-credentials-body">
      <p>These are public accounts for this synthetic demo only. All 17 accounts use the same password. Start with Government, then NORI reception, then the receiving hospital.</p>
      <label>Choose a demo account<select value={selected} onChange={e => { setSelected(e.target.value); setNotice(""); }}>{accounts.map(a => <option key={a.username} value={a.username}>{a.label} · {a.username}</option>)}</select></label>
      <p className="credential-purpose">{account.purpose}</p>
      <div className="credential-row"><div><small>Username</small><code>{account.username}</code></div><button type="button" onClick={() => copy(account.username, "Username")}>Copy username</button></div>
      <div className="credential-row"><div><small>Demo password</small><code>{DEMO_PASSWORD}</code></div><button type="button" onClick={() => copy(DEMO_PASSWORD, "Password")}>Copy password</button></div>
      <div className="credential-actions">{choose && <button type="button" className="primary" onClick={() => { choose(selected); setNotice("Sign-in fields filled. Click Sign in to open this workspace."); }}>Fill sign-in fields</button>}<button type="button" onClick={() => copy(`Username: ${account.username}\nPassword: ${DEMO_PASSWORD}`, "Credentials")}>Copy both</button></div>
      <p className="copy-notice" role="status">{notice}</p>
      <a href="/guide">New here? Read the demo guide →</a>
    </div>
  </details>;
}
