import React, { useState } from 'react';
import ConfirmDialog from './ConfirmDialog';

export default function SourceList({
  article,
  sources,
  selectedSource,
  onSelectSource,
  onSourceAdded,
  onSourceUnlinked,
  onDeleteSource,
  isLoading,
  apiBaseUrl
}) {
  const [newUrl, setNewUrl] = useState('');
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);

  // Source deletion state & dialog
  const [deletingSource, setDeletingSource] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleAddSource = async (e) => {
    e.preventDefault();
    if (!newUrl.trim()) return;

    setAdding(true);
    setError(null);

    try {
      const endpoint = article
        ? `${apiBaseUrl}/articles/${article.id}/sources`
        : `${apiBaseUrl}/sources/snapshot`;

      const res = await fetch(endpoint, {
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

  // Non-destructive: fires immediately without confirmation prompt
  const handleUnlink = async (e, src) => {
    e.stopPropagation();
    if (!article) return;

    setBusyId(src.id);
    setError(null);

    try {
      const res = await fetch(`${apiBaseUrl}/articles/${article.id}/sources/${src.id}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Failed to unlink source (HTTP ${res.status})`);
      }

      if (onSourceUnlinked) {
        await onSourceUnlinked(src.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const promptDeleteSource = (e, src) => {
    e.stopPropagation();
    setDeletingSource(src);
  };

  const confirmDeleteSource = async () => {
    if (!deletingSource) return;
    setIsDeleting(true);
    setError(null);

    try {
      if (onDeleteSource) {
        await onDeleteSource(deletingSource.id);
      } else {
        const res = await fetch(`${apiBaseUrl}/sources/${deletingSource.id}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || data.detail || `Failed to delete source (HTTP ${res.status})`);
        }
        if (onSourceUnlinked) {
          await onSourceUnlinked(deletingSource.id);
        }
      }
      setDeletingSource(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDeleting(false);
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
      {/* Confirm Delete Source Dialog */}
      <ConfirmDialog
        isOpen={!!deletingSource}
        title="Delete Source"
        message="Permanently delete this source and ALL its snapshot history? This cannot be undone."
        confirmText={isDeleting ? 'Deleting...' : 'Delete Source'}
        danger={true}
        onConfirm={confirmDeleteSource}
        onCancel={() => setDeletingSource(null)}
      />

      {/* Header & Add Source Form */}
      <div style={{ padding: '16px', borderBottom: '1px solid #e0e0e0', background: '#fafafa' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#111' }}>
            Tracked Sources ({sources.length})
          </h3>
        </div>
        
        {/* Add Source Form */}
        <form onSubmit={handleAddSource} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              id="add-source-input"
              type="text"
              placeholder="https://example.com/source"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              disabled={adding}
              style={{
                flex: 1,
                padding: '7px 10px',
                fontSize: '13px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                outline: 'none'
              }}
            />
            <button
              id="add-source-btn"
              type="submit"
              disabled={adding || !newUrl.trim()}
              style={{
                padding: '7px 12px',
                fontSize: '13px',
                fontWeight: 600,
                background: '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: adding || !newUrl.trim() ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {adding ? 'Adding...' : 'Add'}
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
          <p style={{ padding: '12px', color: '#777', fontSize: '13px', textAlign: 'center' }}>Loading sources...</p>
        ) : sources.length === 0 ? (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: '#888', fontSize: '13px' }}>
            No sources linked to this article yet.<br />Enter a URL above to start snapshotting.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {sources.map((src) => {
              const isSelected = selectedSource && selectedSource.url === src.url;
              const badge = getStatusBadge(src.status);
              const isBusy = busyId === src.id;

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
                    transition: 'all 0.15s ease',
                    position: 'relative'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: '13px',
                        color: '#212121',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1
                      }}
                      title={src.url}
                    >
                      {src.url}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {article && (
                        <button
                          title="Unlink from this article (keeps snapshot history)"
                          onClick={(e) => handleUnlink(e, src)}
                          disabled={isBusy}
                          style={{
                            background: '#f5f5f5',
                            border: '1px solid #ddd',
                            color: '#666',
                            cursor: isBusy ? 'not-allowed' : 'pointer',
                            padding: '1px 6px',
                            fontSize: '11px',
                            borderRadius: '3px',
                            fontWeight: 500
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = '#d32f2f';
                            e.currentTarget.style.borderColor = '#d32f2f';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#666';
                            e.currentTarget.style.borderColor = '#ddd';
                          }}
                        >
                          Unlink
                        </button>
                      )}

                      <button
                        title="Permanently delete source and all its snapshot history"
                        onClick={(e) => promptDeleteSource(e, src)}
                        disabled={isBusy}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#bbb',
                          cursor: isBusy ? 'not-allowed' : 'pointer',
                          padding: '0 4px',
                          fontSize: '14px',
                          lineHeight: '1',
                          borderRadius: '3px'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#c62828'}
                        onMouseLeave={(e) => e.currentTarget.style.color = '#bbb'}
                      >
                        🗑
                      </button>
                    </div>
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
