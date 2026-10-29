import React, { useState } from 'react';

export default function GenerationChart({ intervals }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  if (!intervals || intervals.length === 0) {
    return (
      <div className="chart-card">
        <div className="chart-header">
          <h3 className="chart-title">Wind Generation: Day-Ahead Forecast vs Outturn</h3>
        </div>
        <div style={{ padding: '60px', textAlign: 'center', color: '#6b7280' }}>
          No interval records available to render chart.
        </div>
      </div>
    );
  }

  // Dimensions
  const svgWidth = 1000;
  const svgHeight = 340;
  // Extra right padding prevents the last x-axis label from being clipped
  const padding = { top: 20, right: 60, bottom: 50, left: 60 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  // Max scale
  const maxGen = Math.max(...intervals.map(i => Math.max(i.actual, i.forecast)), 1000);
  const yMax = Math.ceil((maxGen * 1.1) / 1000) * 1000;

  const getX = (idx) => padding.left + (idx / Math.max(intervals.length - 1, 1)) * chartWidth;
  const getY = (val) => padding.top + chartHeight - (val / yMax) * chartHeight;

  // Path generators
  const actualPoints = intervals.map((d, i) => `${getX(i)},${getY(d.actual)}`).join(' ');
  const forecastPoints = intervals.map((d, i) => `${getX(i)},${getY(d.forecast)}`).join(' ');

  // Y-axis tick marks (5 ticks)
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(ratio => Math.round(yMax * ratio));

  // X-axis tick labels: target ≤ 6 evenly-spaced ticks to prevent label overlap
  const MAX_TICKS = 6;
  const xTickIndices = (() => {
    if (intervals.length <= MAX_TICKS) return intervals.map((_, i) => i);
    const step = Math.floor(intervals.length / (MAX_TICKS - 1));
    const ticks = [];
    for (let i = 0; i < intervals.length - 1; i += step) {
      ticks.push(i);
      if (ticks.length >= MAX_TICKS - 1) break;
    }
    // Include last point only if it won't crowd the prior tick
    const last = intervals.length - 1;
    if (last - ticks[ticks.length - 1] > step / 2) ticks.push(last);
    return ticks;
  })();

  const activePoint = hoverIdx !== null ? intervals[hoverIdx] : null;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Wind Generation: Day-Ahead Forecast vs Outturn</h3>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
            Comparison across {intervals.length} half-hour settlement intervals (MW)
          </div>
        </div>
        <div className="chart-legend">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#10b981' }}></span>
            <span>Actual Outturn (FUELHH)</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#06b6d4' }}></span>
            <span>Selected Forecast (WINDFOR)</span>
          </div>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* Grid lines */}
          {yTicks.map((tick, idx) => {
            const y = getY(tick);
            return (
              <g key={idx}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="#2d3748"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 10}
                  y={y + 4}
                  fill="#9ca3af"
                  fontSize="11"
                  textAnchor="end"
                  fontFamily="var(--font-mono)"
                >
                  {tick.toLocaleString()}
                </text>
              </g>
            );
          })}

          {/* X axis line */}
          <line
            x1={padding.left}
            y1={padding.top + chartHeight}
            x2={svgWidth - padding.right}
            y2={padding.top + chartHeight}
            stroke="#4b5563"
          />

          {/* X axis ticks */}
          {xTickIndices.map((idx) => {
            const x = getX(idx);
            const raw = intervals[idx]?.startTime || '';
            // Format as "DD Mon HH:mm" e.g. "01 Jan 12:00"
            let dateStr = '';
            if (raw) {
              const d = new Date(raw);
              const day = String(d.getUTCDate()).padStart(2, '0');
              const mon = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' });
              const hhmm = raw.substring(11, 16);
              dateStr = `${day} ${mon} ${hhmm}`;
            }
            return (
              <g key={idx}>
                <line x1={x} y1={padding.top + chartHeight} x2={x} y2={padding.top + chartHeight + 6} stroke="#4b5563" />
                <text
                  x={x}
                  y={padding.top + chartHeight + 24}
                  fill="#9ca3af"
                  fontSize="10"
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                >
                  {dateStr}
                </text>
              </g>
            );
          })}

          {/* Actual line (Green) */}
          <polyline
            fill="none"
            stroke="#10b981"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={actualPoints}
          />

          {/* Forecast line (Cyan) */}
          <polyline
            fill="none"
            stroke="#06b6d4"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={forecastPoints}
          />

          {/* Interactive hover overlay regions */}
          {intervals.map((_, idx) => {
            const x = getX(idx);
            const colWidth = chartWidth / intervals.length;
            return (
              <rect
                key={idx}
                x={x - colWidth / 2}
                y={padding.top}
                width={colWidth}
                height={chartHeight}
                fill="transparent"
                onMouseEnter={() => setHoverIdx(idx)}
                style={{ cursor: 'pointer' }}
              />
            );
          })}

          {/* Hover indicator crosshair & dots */}
          {hoverIdx !== null && activePoint && (
            <g>
              <line
                x1={getX(hoverIdx)}
                y1={padding.top}
                x2={getX(hoverIdx)}
                y2={padding.top + chartHeight}
                stroke="#94a3b8"
                strokeWidth="1.5"
                strokeDasharray="3 3"
              />
              <circle
                cx={getX(hoverIdx)}
                cy={getY(activePoint.actual)}
                r="5"
                fill="#10b981"
                stroke="#fff"
                strokeWidth="2"
              />
              <circle
                cx={getX(hoverIdx)}
                cy={getY(activePoint.forecast)}
                r="5"
                fill="#06b6d4"
                stroke="#fff"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>

        {/* Hover Tooltip Box */}
        {hoverIdx !== null && activePoint && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              right: '20px',
              background: 'rgba(17, 24, 39, 0.95)',
              border: '1px solid #374151',
              borderRadius: '8px',
              padding: '12px 16px',
              boxShadow: 'var(--shadow-lg)',
              pointerEvents: 'none',
              fontSize: '12px',
              zIndex: 10,
              minWidth: '220px',
            }}
          >
            <div style={{ fontWeight: '600', color: '#f3f4f6', marginBottom: '6px', fontFamily: 'var(--font-mono)' }}>
              {activePoint.startTime.replace('T', ' ').substring(0, 16)} UTC
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#10b981' }}>Actual Outturn:</span>
              <span style={{ fontWeight: '600', fontFamily: 'var(--font-mono)' }}>{activePoint.actual.toLocaleString()} MW</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#06b6d4' }}>Day-Ahead Forecast:</span>
              <span style={{ fontWeight: '600', fontFamily: 'var(--font-mono)' }}>{activePoint.forecast.toLocaleString()} MW</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #374151', paddingTop: '4px', marginTop: '4px' }}>
              <span style={{ color: activePoint.error >= 0 ? '#f59e0b' : '#3b82f6' }}>Forecast Error:</span>
              <span style={{ fontWeight: '600', fontFamily: 'var(--font-mono)', color: activePoint.error >= 0 ? '#f59e0b' : '#3b82f6' }}>
                {activePoint.error > 0 ? `+${activePoint.error}` : activePoint.error} MW
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
