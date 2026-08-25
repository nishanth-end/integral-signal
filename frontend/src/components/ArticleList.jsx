import React, { useState } from 'react';

export default function ArticleList({
  articles,
  onSelectArticle,
  onArticleCreated,
  isLoading,
  apiBaseUrl
}) {
  const [newTitle, setNewTitle] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const handleCreateArticle = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setCreating(true);
    setError(null);

    try {
      const res = await fetch(`${apiBaseUrl}/articles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle.trim() })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Failed to create article (HTTP ${res.status})`);
      }

      setNewTitle('');
      if (onArticleCreated) {
        await onArticleCreated(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const formatDate = (ts) => {
    if (!ts) return 'Unknown date';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return ts;
    }
  };

  return (
    <div style={{ padding: '32px 40px', maxWidth: '1000px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      {/* Top Banner */}
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{ margin: '0 0 6px 0', fontSize: '24px', fontWeight: 700, color: '#111' }}>
          Articles &amp; Projects
        </h2>
        <p style={{ margin: 0, fontSize: '14px', color: '#666', lineHeight: '1.5' }}>
          Organize and monitor web sources cited across your articles, research projects, and investigations.
        </p>
      </div>

      {/* New Article Creation Form */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          padding: '20px',
          marginBottom: '28px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
        }}
      >
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 600, color: '#222' }}>
          Create New Article
        </h3>
        <form onSubmit={handleCreateArticle} style={{ display: 'flex', gap: '10px' }}>
          <input
            id="new-article-title-input"
            type="text"
            placeholder="e.g. Investigation into Offshore Assets, Tech Policy 2026..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            disabled={creating}
            style={{
              flex: 1,
              padding: '10px 14px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '6px',
              outline: 'none'
            }}
          />
          <button
            id="create-article-btn"
            type="submit"
            disabled={creating || !newTitle.trim()}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              fontWeight: 600,
              background: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: creating || !newTitle.trim() ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
              transition: 'background 0.15s'
            }}
          >
            {creating ? 'Creating...' : '+ New Article'}
          </button>
        </form>
        {error && (
          <div style={{ marginTop: '10px', fontSize: '13px', color: '#c62828', background: '#ffebee', padding: '8px 12px', borderRadius: '4px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Articles Grid */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#333' }}>
            All Articles ({articles.length})
          </h3>
        </div>

        {isLoading && articles.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#777', fontSize: '14px' }}>
            Loading articles...
          </div>
        ) : articles.length === 0 ? (
          <div
            style={{
              padding: '48px 24px',
              textAlign: 'center',
              background: '#ffffff',
              border: '1px dashed #ccc',
              borderRadius: '8px',
              color: '#666'
            }}
          >
            <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '6px', color: '#333' }}>
              No articles yet
            </div>
            <div style={{ fontSize: '13px', color: '#888' }}>
              Create your first article container above to start tracking citation sources.
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '16px'
            }}
          >
            {articles.map((art) => {
              const count = art.source_count || 0;
              return (
                <div
                  key={art.id}
                  id={`article-card-${art.id}`}
                  onClick={() => onSelectArticle(art)}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    padding: '18px 20px',
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                    transition: 'all 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '110px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#1976d2';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.06)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#e0e0e0';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.03)';
                  }}
                >
                  <div>
                    <h4
                      style={{
                        margin: '0 0 8px 0',
                        fontSize: '16px',
                        fontWeight: 600,
                        color: '#1a237e',
                        lineHeight: '1.4',
                        wordBreak: 'break-word'
                      }}
                    >
                      {art.title}
                    </h4>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '12px',
                      color: '#666',
                      marginTop: '12px',
                      borderTop: '1px solid #f0f0f0',
                      paddingTop: '10px'
                    }}
                  >
                    <span
                      style={{
                        background: count > 0 ? '#e8f5e9' : '#f5f5f5',
                        color: count > 0 ? '#2e7d32' : '#777',
                        fontWeight: 600,
                        padding: '3px 8px',
                        borderRadius: '12px'
                      }}
                    >
                      {count === 1 ? '1 tracked source' : `${count} tracked sources`}
                    </span>
                    <span>{formatDate(art.created_at)}</span>
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
