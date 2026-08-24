import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = "http://localhost:8000";

export default function ResearchDashboard() {
  const [query, setQuery] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 1. Submit the research query
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setReport("");
    setStatus("queued");

    try {
      const response = await axios.post(`${API_BASE_URL}/research`, { query });
      // Fixed: backend returns "user_id", not "task_id"
      setTaskId(response.data.user_id);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start research task.");
      setLoading(false);
      setStatus("failed");
    }
  };

  // 2. Poll the backend status endpoint while task is running
  useEffect(() => {
    if (!taskId || status === "completed" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/research/${taskId}`);
        const data = response.data;

        setStatus(data.status);

        if (data.status === "task done successfuly") {
          // Note: matches your backend's actual status string exactly
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
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [taskId, status]);

  return (
    <div style={{ maxWidth: '800px', margin: '40px auto', fontFamily: 'Inter, sans-serif', padding: '0 20px' }}>
      <h2>Market Intelligence Agent</h2>
      <p style={{ color: '#666' }}>Enter a market or startup idea to generate a deep technical research report.</p>

      {/* Input Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., AI-powered logistics tracking startup in Tunisia"
          disabled={loading}
          style={{ flex: 1, padding: '12px', fontSize: '16px', borderRadius: '6px', border: '1px solid #ccc' }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '12px 24px', background: '#0070f3', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          {loading ? 'Researching...' : 'Generate Report'}
        </button>
      </form>

      {/* Error Message */}
      {error && <div style={{ background: '#ffebee', color: '#c62828', padding: '12px', borderRadius: '6px', marginBottom: '20px' }}>{error}</div>}

      {/* Status Tracker */}
      {status && (
        <div style={{ background: '#f5f5f5', padding: '15px', borderRadius: '6px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <strong>Status:</strong>
          <span style={{ textTransform: 'uppercase', fontWeight: 'bold', color: status === 'task done successfuly' ? 'green' : status === 'task failed ! Try again' ? 'red' : '#e65100' }}>
            {status}
          </span>
          {/* Fixed: your actual runs range from ~3 to 11+ minutes, don't hardcode a number */}
          {loading && <span style={{ fontSize: '14px', color: '#666' }}>(This can take several minutes as agents scrape and synthesize data...)</span>}
        </div>
      )}

      {/* Final Report Display */}
      {report && (
        <div style={{ background: '#fff', border: '1px solid #e1e4e8', padding: '30px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h3>Final Market Intelligence Report</h3>
          <hr style={{ border: '0', borderTop: '1px solid #eee', margin: '15px 0' }} />
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', fontSize: '15px', color: '#24292e' }}>
            {report}
          </div>
        </div>
      )}
    </div>
  );
}