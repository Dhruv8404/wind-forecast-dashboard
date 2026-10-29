import React, { useState } from 'react';

export default function ErrorChart({ intervals }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  if (!intervals || intervals.length === 0) {
    return null;
  }

  const svgWidth = 1000;
  const svgHeight = 220;
  const padding = { top: 20, right: 30, bottom: 35, left: 60 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  // Max absolute error for symmetric Y-axis
  const maxAbsErr = Math.max(...intervals.map(i => Math.abs(i.error)), 100);
  const yLimit = Math.ceil((maxAbsErr * 1.15) / 100) * 100;

  const getX = (idx) => padding.left + (idx / Math.max(intervals.length - 1, 1)) * chartWidth;
  const zeroY = padding.top + chartHeight / 2;
  const getY = (errVal) => zeroY - (errVal / yLimit) * (chartHeight / 2);

  const barWidth = Math.max(2, Math.min(16, (chartWidth / intervals.length) * 0.7));

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Forecast Error Distribution (Forecast − Actual)</h3>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
            Positive values indicate over-forecasting (Forecast &gt; Actual); negative indicate under-forecasting
          </div>
        </div>
        <div className="chart-legend">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#f59e0b' }}></span>
            <span>Over-forecast (+)</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#3b82f6' }}></span>
            <span>Under-forecast (−)</span>
          </div>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* Zero reference baseline */}
          <line
            x1={padding.left}
            y1={zeroY}
            x2={svgWidth - padding.right}
            y2={zeroY}
            stroke="#94a3b8"
            strokeWidth="1.5"
          />

          {/* Top & Bottom boundary grid lines */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={svgWidth - padding.right}
            y2={padding.top}
            stroke="#2d3748"
            strokeDasharray="4 4"
          />
          <text
            x={padding.left - 10}
            y={padding.top + 4}
            fill="#9ca3af"
            fontSize="10"
            textAnchor="end"
            fontFamily="var(--font-mono)"
          >
            +{yLimit}
          </text>

          <text
            x={padding.left - 10}
            y={zeroY + 4}
            fill="#e2e8f0"
            fontSize="10"
            textAnchor="end"
            fontFamily="var(--font-mono)"
            fontWeight="bold"
          >
            0 MW
          </text>

          <line
            x1={padding.left}
            y1={padding.top + chartHeight}
            x2={svgWidth - padding.right}
            y2={padding.top + chartHeight}
            stroke="#2d3748"
            strokeDasharray="4 4"
          />
          <text
            x={padding.left - 10}
            y={padding.top + chartHeight + 4}
            fill="#9ca3af"
            fontSize="10"
            textAnchor="end"
            fontFamily="var(--font-mono)"
          >
            -{yLimit}
          </text>

          {/* Bars */}
          {intervals.map((item, idx) => {
            const x = getX(idx);
            const y = getY(item.error);
            const height = Math.abs(y - zeroY);
            const barY = item.error >= 0 ? y : zeroY;
            const color = item.error >= 0 ? '#f59e0b' : '#3b82f6';

            return (
              <g key={idx}>
                <rect
                  x={x - barWidth / 2}
                  y={barY}
                  width={barWidth}
                  height={Math.max(height, 1)}
                  fill={color}
                  rx="1"
                  opacity={hoverIdx === null || hoverIdx === idx ? 0.9 : 0.4}
                />
                {/* Transparent hover column */}
                <rect
                  x={x - (chartWidth / intervals.length) / 2}
                  y={padding.top}
                  width={chartWidth / intervals.length}
                  height={chartHeight}
                  fill="transparent"
                  onMouseEnter={() => setHoverIdx(idx)}
                  style={{ cursor: 'pointer' }}
                />
              </g>
            );
          })}
        </svg>

        {hoverIdx !== null && intervals[hoverIdx] && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              right: '20px',
              background: 'rgba(17, 24, 39, 0.95)',
              border: '1px solid #374151',
              borderRadius: '8px',
              padding: '8px 12px',
              fontSize: '12px',
              pointerEvents: 'none',
              zIndex: 10,
            }}
          >
            <span style={{ color: '#9ca3af', marginRight: '8px' }}>
              {intervals[hoverIdx].startTime.substring(11, 16)} UTC:
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontFamily: 'var(--font-mono)',
                color: intervals[hoverIdx].error >= 0 ? '#f59e0b' : '#3b82f6',
              }}
            >
              {intervals[hoverIdx].error > 0 ? `+${intervals[hoverIdx].error}` : intervals[hoverIdx].error} MW
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
