import React from 'react';

export default function MetricCard({ title, value, unit, subtext, description, accentColor = '#06b6d4' }) {
  return (
    <div className="kpi-card" style={{ borderTop: `3px solid ${accentColor}` }}>
      <div className="kpi-header">
        <span className="kpi-title">{title}</span>
        {subtext && <span className="kpi-sub">{subtext}</span>}
      </div>
      <div className="kpi-value-row">
        <span className="kpi-value">{value !== null && value !== undefined ? value : '--'}</span>
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      {description && <div className="kpi-desc">{description}</div>}
    </div>
  );
}
