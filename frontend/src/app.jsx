import React, { useState, useEffect, useCallback } from 'react';
import SourceList from './components/SourceList';
import DiffView from './components/DiffView';

const SIDECAR_URL = 'http://127.0.0.1:8765';

export default function App() {
  const [health, setHealth] = useState(null);
  const [version, setVersion] = useState(null);
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

  const fetchSources = useCallback(async (selectUrl = null) => {
    setLoadingSources(true);
    try {
      const res = await fetch(`${SIDECAR_URL}/sources`);
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
        } else if (data.sources.length > 0) {
          setSelectedSource(data.sources[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch sources:', err);
    } finally {
      setLoadingSources(false);
    }
  }, [selectedSource]);

  useEffect(() => {
    let intervalId;
    let isMounted = true;

    const poll = async () => {
      const success = await checkSidecar();
      if (success) {
        fetchSources();
      } else if (isMounted) {
        intervalId = setInterval(async () => {
          const ok = await checkSidecar();
          if (ok) {
            clearInterval(intervalId);
            fetchSources();
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif', background: '#fcfcfc', color: '#222' }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 20px',
          background: '#ffffff',
          borderBottom: '1px solid #e0e0e0',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#111' }}>Integral Signal</h1>
          <span style={{ fontSize: '12px', background: '#e0e0e0', padding: '2px 8px', borderRadius: '12px', color: '#555' }}>
            Sources &amp; Diff
          </span>
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

      {/* Two Panel Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Panel: Tracked Sources */}
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
            sources={sources}
            selectedSource={selectedSource}
            onSelectSource={(src) => setSelectedSource(src)}
            onSourceAdded={(newUrl) => fetchSources(newUrl)}
            isLoading={loadingSources}
            apiBaseUrl={SIDECAR_URL}
          />
        </aside>

        {/* Right Panel: Diff & History View */}
        <main style={{ flex: 1, background: '#ffffff', overflowY: 'auto' }}>
          <DiffView
            source={selectedSource}
            apiBaseUrl={SIDECAR_URL}
            onSourceUpdated={() => fetchSources()}
          />
        </main>
      </div>
    </div>
  );
}


