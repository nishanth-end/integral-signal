import React, { useState, useEffect, useCallback } from 'react';
import ArticleList from './components/ArticleList';
import SourceList from './components/SourceList';
import DiffView from './components/DiffView';

const SIDECAR_URL = 'http://127.0.0.1:8765';

export default function App() {
  const [health, setHealth] = useState(null);
  const [version, setVersion] = useState(null);
  
  // Articles state
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [loadingArticles, setLoadingArticles] = useState(false);

  // Sources state (scoped to selectedArticle)
  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);
  const [loadingSources, setLoadingSources] = useState(false);

  const checkSidecar = async () => {
    try {
      const [healthRes, versionRes] = await Promise.all([
        fetch(`${SIDECAR_URL}/health`),
        fetch(`${SIDECAR_URL}/version`)
      ]);

      if (healthRes.ok && versionRes.ok) {
        setHealth(await healthRes.json());
        setVersion(await versionRes.json());
        return true;
      }
    } catch {
      // Backend not yet ready
    }
    return false;
  };

  const fetchArticles = useCallback(async (selectArticleId = null) => {
    setLoadingArticles(true);
    try {
      const res = await fetch(`${SIDECAR_URL}/articles`);
      const data = await res.json();
      if (res.ok && data.articles) {
        setArticles(data.articles);

        if (selectArticleId) {
          const found = data.articles.find(a => a.id === selectArticleId);
          if (found) setSelectedArticle(found);
        } else if (selectedArticle) {
          const current = data.articles.find(a => a.id === selectedArticle.id);
          if (current) setSelectedArticle(current);
        }
      }
    } catch (err) {
      console.error('Failed to fetch articles:', err);
    } finally {
      setLoadingArticles(false);
    }
  }, [selectedArticle]);

  const fetchSources = useCallback(async (selectUrl = null, articleToFetch = selectedArticle) => {
    if (!articleToFetch) {
      setSources([]);
      setSelectedSource(null);
      return;
    }

    setLoadingSources(true);
    try {
      const res = await fetch(`${SIDECAR_URL}/articles/${articleToFetch.id}/sources`);
      const data = await res.json();
      if (res.ok && data.sources) {
        setSources(data.sources);

        // Select specific URL, keep current selection, or select first item
        if (selectUrl) {
          const found = data.sources.find(s => s.url === selectUrl);
          if (found) setSelectedSource(found);
        } else if (selectedSource) {
          const current = data.sources.find(s => s.url === selectedSource.url);
          if (current) setSelectedSource(current);
          else if (data.sources.length > 0) setSelectedSource(data.sources[0]);
          else setSelectedSource(null);
        } else if (data.sources.length > 0) {
          setSelectedSource(data.sources[0]);
        } else {
          setSelectedSource(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch sources for article:', err);
    } finally {
      setLoadingSources(false);
    }
  }, [selectedArticle, selectedSource]);

  // Initial connection poll
  useEffect(() => {
    let intervalId;
    let isMounted = true;

    const poll = async () => {
      const success = await checkSidecar();
      if (success) {
        fetchArticles();
      } else if (isMounted) {
        intervalId = setInterval(async () => {
          const ok = await checkSidecar();
          if (ok) {
            clearInterval(intervalId);
            fetchArticles();
          }
        }, 1000);
      }
    };

    poll();

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  // Fetch sources whenever selectedArticle changes
  useEffect(() => {
    if (selectedArticle) {
      fetchSources(null, selectedArticle);
    } else {
      setSources([]);
      setSelectedSource(null);
    }
  }, [selectedArticle?.id]);

  const handleSelectArticle = (art) => {
    setSelectedSource(null);
    setSelectedArticle(art);
  };

  const handleBackToArticles = () => {
    setSelectedArticle(null);
    setSelectedSource(null);
    fetchArticles();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif', background: '#fcfcfc', color: '#222' }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 20px',
          background: '#ffffff',
          borderBottom: '1px solid #e0e0e0',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
          zIndex: 10
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1
            onClick={handleBackToArticles}
            style={{
              margin: 0,
              fontSize: '17px',
              fontWeight: 700,
              color: '#111',
              cursor: 'pointer'
            }}
            title="Go to Articles"
          >
            Integral Signal
          </h1>

          {selectedArticle ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                id="back-to-articles-btn"
                onClick={handleBackToArticles}
                style={{
                  background: '#f0f0f0',
                  border: '1px solid #d0d0d0',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#444',
                  cursor: 'pointer'
                }}
              >
                &larr; All Articles
              </button>
              <span style={{ color: '#aaa', fontSize: '14px' }}>/</span>
              <span
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  background: '#e3f2fd',
                  color: '#1565c0',
                  padding: '3px 10px',
                  borderRadius: '12px',
                  maxWidth: '300px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}
                title={selectedArticle.title}
              >
                {selectedArticle.title}
              </span>
            </div>
          ) : (
            <span style={{ fontSize: '12px', background: '#e0e0e0', padding: '2px 8px', borderRadius: '12px', color: '#555' }}>
              Articles &amp; Projects
            </span>
          )}
        </div>

        <div style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: health ? '#4caf50' : '#ff9800'
            }}
          />
          <span style={{ color: '#555' }}>
            Sidecar: {health ? `Connected (v${version?.version})` : 'Connecting...'}
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      {!selectedArticle ? (
        <div style={{ flex: 1, overflowY: 'auto', background: '#fcfcfc' }}>
          <ArticleList
            articles={articles}
            onSelectArticle={handleSelectArticle}
            onArticleCreated={async (newArt) => {
              await fetchArticles(newArt.id);
            }}
            isLoading={loadingArticles}
            apiBaseUrl={SIDECAR_URL}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Panel: Scoped Sources for this Article */}
          <aside
            style={{
              width: '320px',
              minWidth: '280px',
              maxWidth: '380px',
              borderRight: '1px solid #e0e0e0',
              background: '#ffffff',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <SourceList
              article={selectedArticle}
              sources={sources}
              selectedSource={selectedSource}
              onSelectSource={(src) => setSelectedSource(src)}
              onSourceAdded={async (newUrl) => {
                await fetchSources(newUrl);
                await fetchArticles();
              }}
              onSourceUnlinked={async (sourceId) => {
                await fetchSources();
                await fetchArticles();
                if (selectedSource?.id === sourceId) {
                  setSelectedSource(null);
                }
              }}
              isLoading={loadingSources}
              apiBaseUrl={SIDECAR_URL}
            />
          </aside>

          {/* Right Panel: Diff & History View */}
          <main style={{ flex: 1, background: '#ffffff', overflowY: 'auto' }}>
            <DiffView
              source={selectedSource}
              apiBaseUrl={SIDECAR_URL}
              onSourceUpdated={async () => {
                await fetchSources();
                await fetchArticles();
              }}
            />
          </main>
        </div>
      )}
    </div>
  );
}
