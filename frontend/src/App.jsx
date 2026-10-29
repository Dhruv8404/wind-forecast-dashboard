import React, { useState, useEffect } from 'react';
import MetricCard from './components/MetricCard';
import GenerationChart from './components/GenerationChart';
import ErrorChart from './components/ErrorChart';
import IntervalsTable from './components/IntervalsTable';
import InsightsPanel from './components/InsightsPanel';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? '' : 'https://wind-forecast-dashboard-eq45.onrender.com')
).replace(/\/+$/, '');

export default function App() {
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState('2026-01-02');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const fetchData = async (start, end) => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = `${API_BASE}/api/accuracy?start_date=${start}&end_date=${end}`;
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
    fetchData(startDate, endDate);
  }, []);

  const handlePreset = (start, end) => {
    setStartDate(start);
    setEndDate(end);
    fetchData(start, end);
  };

  const handleQuery = (e) => {
    e.preventDefault();
    fetchData(startDate, endDate);
  };

  const metrics = data?.count > 0 ? {
    mae: data.mae,
    rmse: data.rmse,
    bias: data.bias,
    count: data.count,
  } : null;

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
          <div className="badge">
            <span className="badge-dot"></span>
            <span>Elexon BMRS Live API</span>
          </div>
          <div className="badge" style={{ background: 'rgba(6, 182, 212, 0.1)', color: '#06b6d4', borderColor: 'rgba(6, 182, 212, 0.2)' }}>
            <span>Cutoff: 10:00 UTC D-1</span>
          </div>
        </div>
      </header>

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

          <button type="submit" className="btn-primary" disabled={loading} style={{ alignSelf: 'flex-end' }}>
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </form>

        <div className="preset-buttons">
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-01-01', '2026-01-02')}
          >
            Jan 1–2, 2026 (Assessment Range)
          </button>
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-01-01', '2026-01-07')}
          >
            Jan 2026 (7-Day Week)
          </button>
          <button
            type="button"
            className="btn-preset"
            onClick={() => handlePreset('2026-10-26', '2026-10-27')}
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
                {data.message || 'No forecast published strictly prior to 10:00 UTC on the day before delivery was found for this date range.'}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
