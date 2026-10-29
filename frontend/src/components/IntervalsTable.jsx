import React, { useState } from 'react';

export default function IntervalsTable({ intervals }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  if (!intervals || intervals.length === 0) {
    return null;
  }

  const filtered = intervals.filter(i =>
    i.startTime.includes(searchTerm) || (i.forecastPublishTime && i.forecastPublishTime.includes(searchTerm))
  );

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  const downloadCSV = () => {
    const headers = ['Delivery Interval (UTC)', 'Forecast Publish Time (UTC)', 'Forecast (MW)', 'Actual (MW)', 'Error (MW)', 'Absolute Error (MW)'];
    const rows = filtered.map(item => [
      item.startTime,
      item.forecastPublishTime || '',
      item.forecast,
      item.actual,
      item.error,
      item.absoluteError,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `wind_forecast_accuracy_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="table-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 className="chart-title">Settlement Intervals Audit ({filtered.length} intervals)</h3>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
            Strictly aligns outturn with the latest eligible forecast published before the 10:00 UTC day-ahead cutoff
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Filter timestamp (e.g. 12:00)..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
            style={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              outline: 'none',
              width: '220px'
            }}
          />
          <button
            onClick={downloadCSV}
            className="btn-preset"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '500' }}
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Delivery Interval (UTC)</th>
              <th>Eligible Publish Time (UTC)</th>
              <th style={{ textAlign: 'right' }}>Forecast (MW)</th>
              <th style={{ textAlign: 'right' }}>Actual Outturn (MW)</th>
              <th style={{ textAlign: 'right' }}>Error (MW)</th>
              <th style={{ textAlign: 'right' }}>|Error| (MW)</th>
              <th>Direction</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((item, idx) => (
              <tr key={idx}>
                <td style={{ color: '#f3f4f6', fontWeight: '500' }}>
                  {item.startTime.replace('T', ' ').substring(0, 16)}
                </td>
                <td style={{ color: '#9ca3af' }}>
                  {item.forecastPublishTime ? item.forecastPublishTime.replace('T', ' ').substring(0, 16) : 'N/A'}
                </td>
                <td style={{ textAlign: 'right', color: '#06b6d4', fontWeight: '600' }}>
                  {item.forecast.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                </td>
                <td style={{ textAlign: 'right', color: '#10b981', fontWeight: '600' }}>
                  {item.actual.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                </td>
                <td style={{ textAlign: 'right', fontWeight: '600', color: item.error >= 0 ? '#f59e0b' : '#3b82f6' }}>
                  {item.error > 0 ? `+${item.error.toFixed(1)}` : item.error.toFixed(1)}
                </td>
                <td style={{ textAlign: 'right', color: '#cbd5e1' }}>
                  {item.absoluteError.toFixed(1)}
                </td>
                <td>
                  {item.error >= 0 ? (
                    <span className="tag-positive">Over-forecast</span>
                  ) : (
                    <span className="tag-negative">Under-forecast</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', fontSize: '13px', color: '#9ca3af' }}>
          <span>Showing page {page} of {totalPages}</span>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-preset"
              style={{ opacity: page === 1 ? 0.5 : 1, cursor: page === 1 ? 'not-allowed' : 'pointer' }}
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-preset"
              style={{ opacity: page === totalPages ? 0.5 : 1, cursor: page === totalPages ? 'not-allowed' : 'pointer' }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
