import React, { useState, useEffect } from 'react';
import MetricCard from './components/MetricCard';
import GenerationChart from './components/GenerationChart';
import ErrorChart from './components/ErrorChart';
import IntervalsTable from './components/IntervalsTable';
import InsightsPanel from './components/InsightsPanel';

// Reads Vite environment variable when supplied; defaults to relative URL ('')
// so Vite dev proxy and Nginx production reverse proxy work seamlessly without hardcoded hostnames.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export default function App() {
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState('2026-01-02');
  const [cutoffHour, setCutoffHour] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const fetchData = async (start, end, cutoff = cutoffHour) => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = `${API_BASE}/api/accuracy?start_date=${start}&end_date=${end}&cutoff_hour=${cutoff}`;
      const response = await fetch(endpoint);

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      setData(json);
    } catch (err) {
      console.error('Failed to fetch accuracy data:', err);
      setError(err.message || 'An error occurred while communicating with the backend API.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(startDate, endDate, cutoffHour);
  }, []);

  const handlePreset = (start, end, cutoff = 10) => {
    setStartDate(start);
    setEndDate(end);
    setCutoffHour(cutoff);
    fetchData(start, end, cutoff);
  };

  const handleQuery = (e) => {
    e.preventDefault();
    fetchData(startDate, endDate, cutoffHour);
  };

  const metrics = data?.count > 0 ? {
    mae: data.mae,
    rmse: data.rmse,
    bias: data.bias,
    count: data.count,
  } : null;

  const isSynthetic = data?.data_source === 'synthetic';

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="header-bar">
        <div className="header-title-group">
          <div className="logo-icon">💨</div>
          <div>
            <h1 className="title-text">UK Wind Generation Forecast Intelligence</h1>
            <div className="subtitle-text">
              National Balancing Mechanism Outturn (FUELHH) vs Day-Ahead Forecasts (WINDFOR)
            </div>
          </div>
        </div>

        <div className="header-badges">
          {isSynthetic ? (
            <div
              className="badge"
              style={{
                background: 'rgba(245, 158, 11, 0.15)',
                color: '#f59e0b',
                borderColor: 'rgba(245, 158, 11, 0.35)',
              }}
              title={data?.fallback_reason || 'Simulated synthetic GB wind data in use'}
            >
              <span
                className="badge-dot"
                style={{ background: '#f59e0b', boxShadow: '0 0 8px rgba(245, 158, 11, 0.6)' }}
              ></span>
              <span>Synthetic Fallback Profile</span>
            </div>
          ) : (
            <div className="badge">
              <span className="badge-dot"></span>
              <span>Elexon BMRS Live API</span>
            </div>
          )}

          <div
            className="badge"
            style={{
              background: 'rgba(6, 182, 212, 0.1)',
              color: '#06b6d4',
              borderColor: 'rgba(6, 182, 212, 0.2)',
            }}
          >
            <span>Cutoff: {data?.decision_cutoff || `${cutoffHour}:00 UTC D-1`}</span>
          </div>
        </div>
      </header>

      {/* Synthetic Fallback Notice Banner */}
      {isSynthetic && (
        <div
          className="synthetic-notice"
          style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderLeft: '4px solid #f59e0b',
            borderRadius: '8px',
            padding: '12px 18px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '20px' }}>⚠️</span>
          <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.4' }}>
            <strong style={{ color: '#f59e0b' }}>Synthetic Fallback Active:</strong> Live Elexon BMRS API records were
            not retrievable for this query ({data.fallback_reason || 'offline or empty response'}). Rendering
            a deterministic synthetic GB wind profile (3,000–16,000 MW) to verify UI components, metrics, and cutoff logic.
          </div>
        </div>
      )}

      {/* Controls & Filter Panel */}
      <div className="controls-card">
        <form onSubmit={handleQuery} className="date-controls">
          <div className="input-group">
            <label className="input-label">Delivery Start Date</label>
            <input
              type="date"
              className="date-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>

          <div className="input-group">
            <label className="input-label">Delivery End Date</label>
            <input
              type="date"
              className="date-input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>

          <div className="input-group">
            <label className="input-label">Decision Cutoff (D-1 UTC)</label>
            <select
              className="date-input"
              value={cutoffHour}
              onChange={(e) => setCutoffHour(Number(e.target.value))}
            >
              <option value="9">09:00 UTC D-1</option>
              <option value="10">10:00 UTC D-1 (Standard)</option>
              <option value="11">11:00 UTC D-1</option>
              <option value="12">12:00 UTC D-1</option>
              <option value="17">17:00 UTC D-1</option>
            </select>
          </div>

          <button type="submit" className="btn-primary" disabled={loading} style={{ alignSelf: 'flex-end' }}>
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </form>

        <div className="preset-buttons">
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-01-01', '2026-01-02', 10)}
          >
            Jan 1–2, 2026 (Assessment Range)
          </button>
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-01-01', '2026-01-07', 10)}
          >
            Jan 2026 (7-Day Week)
          </button>
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-01-01', '2026-01-31', 10)}
          >
            Jan 2026 (Full Month)
          </button>
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-10-26', '2026-10-27', 10)}
          >
            Recent 48h Outturn
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="error-box" style={{ borderLeft: '4px solid #f43f5e' }}>
          <div style={{ color: '#f43f5e', fontWeight: '600', marginBottom: '4px' }}>API Error</div>
          <div style={{ color: '#cbd5e1', fontSize: '13px' }}>{error}</div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="loading-box">
          <div className="spinner"></div>
          <div style={{ color: '#9ca3af', fontSize: '13px' }}>
            Fetching outturn and aligning day-ahead forecasts across half-hourly settlement intervals...
          </div>
        </div>
      )}

      {/* Main Dashboard Content */}
      {!loading && data && (
        <>
          {/* KPI Metrics Grid */}
          <div className="kpi-grid">
            <MetricCard
              title="Mean Absolute Error (MAE)"
              value={metrics?.mae}
              unit="MW"
              subtext="Average Deviation"
              description="Mean of absolute error |Forecast − Actual| across all evaluated half-hours."
              accentColor="#06b6d4"
            />
            <MetricCard
              title="Root Mean Square Error (RMSE)"
              value={metrics?.rmse}
              unit="MW"
              subtext="Outlier Sensitivity"
              description="Penalizes large extreme misses more heavily due to quadratic error squaring."
              accentColor="#3b82f6"
            />
            <MetricCard
              title="Systematic Forecast Bias"
              value={metrics?.bias !== undefined ? (metrics.bias > 0 ? `+${metrics.bias}` : metrics.bias) : '--'}
              unit="MW"
              subtext={metrics?.bias > 0 ? 'Over-forecasting' : 'Under-forecasting'}
              description="Average signed error (Forecast − Actual). Positive confirms systematic over-estimation."
              accentColor={metrics?.bias > 0 ? '#f59e0b' : '#10b981'}
            />
            <MetricCard
              title="Matched Settlement Intervals"
              value={data.count}
              unit="Periods"
              subtext="48 per 24h day"
              description="Half-hourly trading intervals paired strictly with eligible day-ahead forecasts."
              accentColor="#10b981"
            />
          </div>

          {/* Visualizations */}
          {data.count > 0 && (
            <div className="charts-grid">
              <GenerationChart intervals={data.intervals} />
              <ErrorChart intervals={data.intervals} />
            </div>
          )}

          {/* Domain Insights Panel */}
          <InsightsPanel bias={metrics?.bias} />

          {/* Granular Audit Table */}
          {data.count > 0 && (
            <IntervalsTable intervals={data.intervals} />
          )}

          {data.count === 0 && (
            <div className="loading-box">
              <div style={{ fontSize: '18px', fontWeight: '600', color: '#f3f4f6', marginBottom: '8px' }}>
                No Matching Settlement Intervals
              </div>
              <p style={{ color: '#9ca3af', fontSize: '13px', maxWidth: '540px', margin: '0 auto' }}>
                {data.message || `No forecast published strictly prior to ${cutoffHour}:00 UTC on the day before delivery was found for this date range.`}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
