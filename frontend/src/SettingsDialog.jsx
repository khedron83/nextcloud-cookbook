import React, { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function SettingsDialog({ settings, onClose, onSaved }) {
  const [url, setUrl] = useState(settings.url || "");
  const [username, setUsername] = useState(settings.username || "");
  const [password, setPassword] = useState(settings.password || "");
  const [verifySsl, setVerifySsl] = useState(settings.verify_ssl ?? true);
  const [status, setStatus] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const s = { url: url || null, username: username || null, password: password || null, verify_ssl: verifySsl };
      await invoke("save_settings", { s });
      onSaved(s);
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    if (!url || !username) { setStatus({ ok: false, msg: "URL and username required." }); return; }
    setTesting(true); setStatus(null);
    try {
      const v = await invoke("test_connection", { url, username, password, verifySsl });
      setStatus({ ok: true, msg: `Connected — cookbook v${v}` });
    } catch (e) {
      setStatus({ ok: false, msg: String(e) });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog">
        <h2>Nextcloud Settings</h2>

        <div className="form-group">
          <label>Server URL</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://cloud.example.com" />
        </div>
        <div className="form-group">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="your-username" />
        </div>
        <div className="form-group">
          <label>Password / App password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          <span className="dialog-path" style={{ display: "block", marginTop: 4 }}>
            Use an app password from Nextcloud → Settings → Security.
          </span>
        </div>
        <div className="form-group">
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", textTransform: "none" }}>
            <input type="checkbox" checked={verifySsl} onChange={(e) => setVerifySsl(e.target.checked)} />
            Verify SSL certificate
          </label>
          {!verifySsl && (
            <span className="dialog-path" style={{ color: "#fbbf24", display: "block", marginTop: 4 }}>
              Disabled — accepts self-signed certificates.
            </span>
          )}
        </div>

        {status && (
          <div className={`dialog-status ${status.ok ? "ok" : "err"}`}>{status.msg}</div>
        )}

        <div className="dialog-row">
          <button className="btn-ghost" onClick={test} disabled={testing}>
            {testing ? "Testing…" : "Test Connection"}
          </button>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={save} disabled={saving}>Save</button>
        </div>
      </div>
    </div>
  );
}
