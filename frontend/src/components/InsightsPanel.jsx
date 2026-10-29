import React from 'react';

export default function InsightsPanel({ bias }) {
  const isPositive = bias !== null && bias > 0;

  return (
    <div className="insights-card">
      <div className="insights-header">
        <span>Engineering &amp; Market Analysis: Forecast Error Characteristics</span>
      </div>
      <div className="insights-body">
        {isPositive && (
          <p style={{ marginBottom: '8px' }}>
            <strong>Observed Systematic Positive Bias (+{bias} MW):</strong> The analysis shows that day-ahead wind
            forecasts exceed actual metered generation outturn (Forecast &gt; Actual) across this date range.
            Several factors <em>may</em> contribute to this pattern in the UK electricity market — these are
            potential explanations rather than confirmed causes for the specific values shown:
          </p>
        )}
        {!isPositive && (
          <p style={{ marginBottom: '8px' }}>
            <strong>Grid Physics &amp; Forecast Accuracy Evaluation:</strong> Wind power forecasting differs from
            conventional dispatchable power due to atmospheric dynamics and transmission constraints. The following
            are <em>potential contributing factors</em> that may explain why forecast errors tend to skew positive in
            the UK — they should be interpreted as domain context, not definitive conclusions:
          </p>
        )}

        <div className="insights-grid">
          <div className="insight-point">
            <div className="insight-point-title">1. Transmission Curtailment (B6 Boundary) — Potential Factor</div>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>
              Scotland and northern offshore wind farms can produce more power than transmission lines (such as the
              Anglo-Scottish B6 boundary) can physically carry south. When lines reach thermal limits, NESO may issue
              Bid-Offer Acceptance (BOA) instructions requiring wind operators to reduce generation. In such cases
              the meteorological wind potential exists in WINDFOR, but metered delivery in FUELHH is lower due to
              curtailment. Whether this occurred in the selected period requires operational dispatch data to confirm.
            </p>
          </div>

          <div className="insight-point">
            <div className="insight-point-title">2. Unconstrained Potential vs Metered Outturn — Structural Difference</div>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>
              WINDFOR models unconstrained physical generation capability based on numerical weather predictions
              (NWP). In contrast, FUELHH measures net electricity actually delivered into the transmission grid,
              which can be lower post-curtailment or due to availability constraints. This structural difference
              tends to produce a positive directional bias (Forecast &gt; Actual) in aggregate statistics.
            </p>
          </div>

          <div className="insight-point">
            <div className="insight-point-title">3. High Wind Speed Cut-Out Protection — Potential Factor</div>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>
              During severe storm events exceeding ~25 m/s, wind turbines automatically shut down to prevent
              mechanical failure. If atmospheric models underestimate peak gusts or cut-out hysteresis, forecasts
              may assume near-maximum capacity while actual output drops sharply. Whether this contributed to the
              errors in this specific period cannot be determined from generation data alone.
            </p>
          </div>

          <div className="insight-point">
            <div className="insight-point-title">4. Asymmetric Balancing Risks — Contextual Factor</div>
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>
              System operators and market participants face asymmetric balancing penalties. Sudden shortfalls may
              require expensive fast-start open-cycle gas turbines (OCGT), whereas modest excess wind can be
              curtailed or absorbed via interconnectors and pumped storage. These incentives may influence how
              forecasts are produced and how operators respond — but their effect on the specific error magnitude
              shown here would require further analysis.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
