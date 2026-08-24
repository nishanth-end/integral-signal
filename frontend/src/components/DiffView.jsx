import React, { useState, useEffect } from 'react';

export default function DiffView({
  source,
  apiBaseUrl,
  onSourceUpdated
}) {
  const [checking, setChecking] = useState(false);
  const [diffResult, setDiffResult] = useState(null);
  const [diffError, setDiffError] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchHistory = async () => {
    if (!source || !source.url) return;
    setHistoryLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/sources/history?url=${encodeURIComponent(source.url)}`);
      const data = await res.json();
      if (res.ok && data.history) {
        setHistory(data.history);
      }
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    setDiffResult(null);
    setDiffError(null);
    fetchHistory();
  }, [source?.url]);

  const handleCheckNow = async () => {
    if (!source || !source.url) return;
    setChecking(true);
    setDiffError(null);

    try {
      const res = await fetch(`${apiBaseUrl}/sources/diff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: source.url })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Diff check failed (HTTP ${res.status})`);
      }

      setDiffResult(data);
      // Refresh history and source list
      await fetchHistory();
      if (onSourceUpdated) {
        await onSourceUpdated(source.url);
      }
    } catch (err) {
      setDiffError(err.message);
    } finally {
      setChecking(false);
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Unknown';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' on ' + d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return ts;
    }
  };

  if (!source) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#888' }}>
        Select a source from the list to view diff &amp; history.
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', height: '100%', boxSizing: 'border-box', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #eee', paddingBottom: '16px', marginBottom: '20px' }}>
        <div style={{ flex: 1, marginRight: '16px' }}>
          <span style={{ fontSize: '12px', color: '#777', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px' }}>Tracked Source</span>
          <h2 style={{ margin: '4px 0 6px 0', fontSize: '18px', wordBreak: 'break-all' }}>
            <a href={source.url} target="_blank" rel="noreferrer" style={{ color: '#1976d2', textDecoration: 'none' }}>
              {source.url}
            </a>
          </h2>
          <div style={{ fontSize: '12px', color: '#666' }}>
            Added: {formatTimestamp(source.created_at)} &bull; Total snapshots: {source.snapshot_count || history.length}
          </div>
        </div>

        <button
          id="check-now-btn"
          onClick={handleCheckNow}
          disabled={checking}
          style={{
            padding: '8px 18px',
            fontSize: '14px',
            fontWeight: 600,
            background: '#2e7d32',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: checking ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap'
          }}
        >
          {checking ? 'Checking...' : 'Check now'}
        </button>
      </div>

      {/* Diff Result Box */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '15px', margin: '0 0 10px 0' }}>Latest Check Result</h3>

        {diffError && (
          <div style={{ padding: '12px', background: '#ffebee', color: '#c62828', borderRadius: '6px', fontSize: '13px' }}>
            <strong>Error checking source:</strong> {diffError}
          </div>
        )}

        {!diffError && !diffResult && (
          <div style={{ padding: '12px 16px', background: '#f9f9f9', border: '1px dashed #ddd', borderRadius: '6px', fontSize: '13px', color: '#666' }}>
            Click <strong>Check now</strong> above to compare the live source against the stored snapshot.
          </div>
        )}

        {diffResult && diffResult.status === 'no_change' && (
          <div style={{ padding: '12px 16px', background: '#e8f5e9', border: '1px solid #c8e6c9', color: '#2e7d32', borderRadius: '6px', fontSize: '13px' }}>
            <strong>No changes detected.</strong> Content is identical to the baseline snapshot from {formatTimestamp(diffResult.timestamp)}.
          </div>
        )}

        {diffResult && diffResult.status === 'no_prior_snapshot' && (
          <div style={{ padding: '12px 16px', background: '#fff3e0', border: '1px solid #ffe0b2', color: '#e65100', borderRadius: '6px', fontSize: '13px' }}>
            No prior snapshot found. Initial snapshot has been created.
          </div>
        )}

        {diffResult && diffResult.status === 'changes_detected' && (
          <div>
            <div style={{ padding: '10px 14px', background: '#fff3e0', border: '1px solid #ffe0b2', color: '#e65100', borderRadius: '6px 6px 0 0', fontSize: '13px', fontWeight: 600 }}>
              Changes detected compared to snapshot from {formatTimestamp(diffResult.previous_timestamp)}:
            </div>
            <div
              style={{
                background: '#1e1e1e',
                color: '#d4d4d4',
                padding: '12px',
                borderRadius: '0 0 6px 6px',
                fontFamily: 'monospace',
                fontSize: '12px',
                maxHeight: '300px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.5'
              }}
            >
              {diffResult.diff && diffResult.diff.length > 0 ? (
                diffResult.diff.map((line, idx) => {
                  let lineStyle = { color: '#d4d4d4' };
                  if (line.startsWith('+')) {
                    lineStyle = { color: '#81c784', background: 'rgba(76, 175, 80, 0.15)', display: 'block' };
                  } else if (line.startsWith('-')) {
                    lineStyle = { color: '#e57373', background: 'rgba(244, 67, 54, 0.15)', display: 'block' };
                  } else if (line.startsWith('@@')) {
                    lineStyle = { color: '#64b5f6', fontWeight: 'bold', display: 'block' };
                  }
                  return <span key={idx} style={lineStyle}>{line}{'\n'}</span>;
                })
              ) : (
                <span>(Diff details unavailable)</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Snapshot History */}
      <div>
        <h3 style={{ fontSize: '15px', margin: '0 0 10px 0' }}>Snapshot History ({history.length})</h3>
        {historyLoading ? (
          <p style={{ color: '#777', fontSize: '13px' }}>Loading history...</p>
        ) : history.length === 0 ? (
          <p style={{ color: '#777', fontSize: '13px' }}>No snapshots recorded.</p>
        ) : (
          <div style={{ border: '1px solid #e0e0e0', borderRadius: '6px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #e0e0e0' }}>
                  <th style={{ padding: '8px 12px' }}>Snapshot Time</th>
                  <th style={{ padding: '8px 12px' }}>Trigger</th>
                  <th style={{ padding: '8px 12px' }}>Content Hash</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '8px 12px', color: '#333' }}>
                      {formatTimestamp(item.fetched_at)}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span
                        style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 600,
                          background: item.trigger === 'manual' ? '#e3f2fd' : '#f3e5f5',
                          color: item.trigger === 'manual' ? '#1565c0' : '#7b1fa2'
                        }}
                      >
                        {item.trigger || 'manual'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#666' }}>
                      {item.content_hash ? item.content_hash.slice(0, 16) + '...' : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
