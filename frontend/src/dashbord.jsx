import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = "http://localhost:8000";

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(180deg, #fafafa 0%, #f3f4f6 100%)',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    padding: '48px 24px',
  },
  container: {
    maxWidth: '780px',
    margin: '0 auto',
  },
  header: {
    textAlign: 'center',
    marginBottom: '40px',
  },
  eyebrow: {
    display: 'inline-block',
    fontSize: '12px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#6366f1',
    background: '#eef2ff',
    padding: '4px 12px',
    borderRadius: '999px',
    marginBottom: '16px',
  },
  title: {
    fontSize: '34px',
    fontWeight: 700,
    color: '#111827',
    margin: '0 0 10px 0',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    fontSize: '16px',
    color: '#6b7280',
    margin: 0,
    lineHeight: 1.5,
  },
  card: {
    background: '#ffffff',
    borderRadius: '16px',
    padding: '8px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)',
    border: '1px solid #eef0f3',
  },
  formRow: {
    display: 'flex',
    gap: '8px',
    padding: '8px',
  },
  input: {
    flex: 1,
    padding: '14px 16px',
    fontSize: '15px',
    borderRadius: '10px',
    border: '1px solid transparent',
    background: '#f9fafb',
    outline: 'none',
    color: '#111827',
    transition: 'border-color 0.15s, background 0.15s',
  },
  button: {
    padding: '14px 22px',
    fontSize: '15px',
    fontWeight: 600,
    color: '#fff',
    background: '#111827',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'background 0.15s, transform 0.1s',
  },
  buttonDisabled: {
    background: '#9ca3af',
    cursor: 'not-allowed',
  },
  spinner: {
    width: '14px',
    height: '14px',
    border: '2px solid rgba(255,255,255,0.4)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.7s linear infinite',
  },
  errorBox: {
    marginTop: '20px',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#991b1b',
    padding: '14px 18px',
    borderRadius: '12px',
    fontSize: '14px',
    lineHeight: 1.5,
  },
  statusBox: {
    marginTop: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px 20px',
    borderRadius: '12px',
    background: '#ffffff',
    border: '1px solid #eef0f3',
  },
  statusLabel: {
    fontSize: '13px',
    fontWeight: 600,
    letterSpacing: '0.03em',
    textTransform: 'uppercase',
  },
  statusHint: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  reportCard: {
    marginTop: '28px',
    background: '#ffffff',
    borderRadius: '16px',
    border: '1px solid #eef0f3',
    boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)',
    overflow: 'hidden',
  },
  reportHeader: {
    padding: '22px 28px',
    borderBottom: '1px solid #f3f4f6',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  reportTitle: {
    fontSize: '17px',
    fontWeight: 700,
    color: '#111827',
    margin: 0,
  },
  reportBadge: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#059669',
    background: '#ecfdf5',
    padding: '4px 10px',
    borderRadius: '999px',
    letterSpacing: '0.03em',
  },
  reportBody: {
    padding: '28px',
    whiteSpace: 'pre-wrap',
    lineHeight: 1.7,
    fontSize: '14.5px',
    color: '#1f2937',
    maxHeight: '640px',
    overflowY: 'auto',
  },
};

const statusMeta = {
  idle: { color: '#9ca3af', label: '' },
  queued: { color: '#f59e0b', label: 'Queued' },
  running: { color: '#3b82f6', label: 'Running' },
  'task done successfuly': { color: '#10b981', label: 'Completed' },
  'task failed ! Try again': { color: '#ef4444', label: 'Failed' },
};

export default function ResearchDashboard() {
  const [query, setQuery] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setReport("");
    setStatus("queued");

    try {
      const response = await axios.post(`${API_BASE_URL}/research`, { query });
      setTaskId(response.data.user_id);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start research task.");
      setLoading(false);
      setStatus(null);
    }
  };

  useEffect(() => {
    if (!taskId || status === "task done successfuly" || status === "task failed ! Try again") return;

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/research/${taskId}`);
        const data = response.data;

        setStatus(data.status);

        if (data.status === "task done successfuly") {
          setReport(data.response);
          setLoading(false);
          clearInterval(interval);
        } else if (data.status === "task failed ! Try again") {
          setError(data.response || "Research task failed on the server.");
          setLoading(false);
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId, status]);

  const meta = statusMeta[status] || statusMeta.idle;

  return (
    <div style={styles.page}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input::placeholder { color: #9ca3af; }
        input:focus { background: #fff !important; border-color: #111827 !important; }
        button:not(:disabled):hover { background: #1f2937 !important; }
        button:not(:disabled):active { transform: scale(0.98); }
      `}</style>

      <div style={styles.container}>
        <div style={styles.header}>
          <span style={styles.eyebrow}>AI Market Research</span>
          <h1 style={styles.title}>Market Intelligence Agent</h1>
          <p style={styles.subtitle}>
            Enter a market or startup idea to generate a deep technical research report.
          </p>
        </div>

        <div style={styles.card}>
          <form onSubmit={handleSubmit} style={styles.formRow}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., AI-powered logistics tracking startup in Tunisia"
              disabled={loading}
              style={styles.input}
            />
            <button
              type="submit"
              disabled={loading}
              style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
            >
              {loading && <span style={styles.spinner} />}
              {loading ? 'Researching' : 'Generate Report'}
            </button>
          </form>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        {status && (
          <div style={styles.statusBox}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: meta.color, boxShadow: `0 0 0 4px ${meta.color}22`, flexShrink: 0 }} />
            <span style={{ ...styles.statusLabel, color: meta.color }}>{meta.label || status}</span>
            {loading && <span style={styles.statusHint}>This can take several minutes as agents scrape and synthesize data&hellip;</span>}
          </div>
        )}

        {report && (
          <div style={styles.reportCard}>
            <div style={styles.reportHeader}>
              <h3 style={styles.reportTitle}>Final Market Intelligence Report</h3>
              <span style={styles.reportBadge}>Ready</span>
            </div>
            <div style={styles.reportBody}>{report}</div>
          </div>
        )}
      </div>
    </div>
  );
}