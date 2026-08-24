import React, { useState } from 'react';

export default function SourceList({
  sources,
  selectedSource,
  onSelectSource,
  onSourceAdded,
  isLoading,
  apiBaseUrl
}) {
  const [newUrl, setNewUrl] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);

  const handleAddSource = async (e) => {
    e.preventDefault();
    if (!newUrl.trim()) return;

    setAdding(true);
    setError(null);

    try {
      const res = await fetch(`${apiBaseUrl}/sources/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newUrl.trim() })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Failed to add source (HTTP ${res.status})`);
      }

      setNewUrl('');
      if (onSourceAdded) {
        await onSourceAdded(data.url);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'no_change':
        return {
          label: 'No changes',
          color: '#2e7d32',
          bg: '#e8f5e9',
          dot: '#4caf50'
        };
      case 'changed':
        return {
          label: 'Changed',
          color: '#e65100',
          bg: '#fff3e0',
          dot: '#ff9800'
        };
      case 'initial':
      default:
        return {
          label: 'Initial snapshot',
          color: '#555555',
          bg: '#eeeeee',
          dot: '#9e9e9e'
        };
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Never';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return ts;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #e0e0e0' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>Tracked Sources ({sources.length})</h3>
        
        {/* Add Source Form */}
        <form onSubmit={handleAddSource} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              id="add-source-input"
              type="text"
              placeholder="https://example.com/article"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              disabled={adding}
              style={{
                flex: 1,
                padding: '6px 8px',
                fontSize: '13px',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            />
            <button
              id="add-source-btn"
              type="submit"
              disabled={adding || !newUrl.trim()}
              style={{
                padding: '6px 12px',
                fontSize: '13px',
                background: '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: adding || !newUrl.trim() ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {adding ? 'Adding...' : 'Add Source'}
            </button>
          </div>
          {error && (
            <div style={{ fontSize: '12px', color: '#c62828', background: '#ffebee', padding: '6px 8px', borderRadius: '4px' }}>
              {error}
            </div>
          )}
        </form>
      </div>

      {/* Sources List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {isLoading && sources.length === 0 ? (
          <p style={{ padding: '12px', color: '#777', fontSize: '13px' }}>Loading sources...</p>
        ) : sources.length === 0 ? (
          <div style={{ padding: '16px', textAlign: 'center', color: '#888', fontSize: '13px' }}>
            No sources tracked yet. Enter a URL above to start snapshotting.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {sources.map((src) => {
              const isSelected = selectedSource && selectedSource.url === src.url;
              const badge = getStatusBadge(src.status);

              return (
                <div
                  key={src.id}
                  id={`source-item-${src.id}`}
                  data-url={src.url}
                  onClick={() => onSelectSource(src)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    background: isSelected ? '#e3f2fd' : '#ffffff',
                    border: isSelected ? '1px solid #90caf9' : '1px solid #e0e0e0',
                    boxShadow: isSelected ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >

                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: '13px',
                      color: '#212121',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      marginBottom: '4px'
                    }}
                    title={src.url}
                  >
                    {src.url}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: '#666' }}>
                    <span>Checked: {formatTimestamp(src.last_checked)}</span>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 6px',
                        borderRadius: '10px',
                        background: badge.bg,
                        color: badge.color,
                        fontWeight: 500
                      }}
                    >
                      <span
                        style={{
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          background: badge.dot
                        }}
                      />
                      {badge.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
