import { useState } from "react";
import { rupees, initials, avatarColor } from "../format.js";

// Shows who fronted the money and the transactions to settle. Two views:
// "Simplified" = fewest transactions (netted); "Detailed" = every direct debt,
// tagged with what it's for. The toggle only appears when they actually differ.
export default function SettleUp({
  settlements = [],
  settlementsDetailed = [],
  paidBy = {},
  people = [],
}) {
  const hasDetailed = settlementsDetailed.length > settlements.length;
  const [detailed, setDetailed] = useState(false);

  if (!settlements.length) return null;

  const payers = Object.entries(paidBy);
  const list = detailed && hasDetailed ? settlementsDetailed : settlements;

  return (
    <div>
      <div className="settle-head">
        <div className="section-title">Settle up</div>
        {hasDetailed && (
          <div className="toggle" role="group" aria-label="Settlement view">
            <button
              className={!detailed ? "toggle-btn active" : "toggle-btn"}
              onClick={() => setDetailed(false)}
            >
              Simplified
            </button>
            <button
              className={detailed ? "toggle-btn active" : "toggle-btn"}
              onClick={() => setDetailed(true)}
            >
              Detailed
            </button>
          </div>
        )}
      </div>

      {payers.length > 0 && (
        <p className="paid-by">
          {payers.map(([name, amount], i) => (
            <span key={name}>
              {i > 0 && ", "}
              <strong>{name}</strong> paid {rupees(amount)}
            </span>
          ))}
        </p>
      )}

      <div className="settle-list">
        {list.map((t, i) => {
          const upiNote = encodeURIComponent(`FinSplit: ${t.from} pays ${t.to}`);
          const upiHref = `upi://pay?am=${t.amount}&tn=${upiNote}&cu=INR`;
          return (
            <div className="settle-row" key={i}>
              <span className="settle-party">
                <span
                  className="avatar avatar-sm"
                  style={{ background: avatarColor(t.from, people) }}
                >
                  {initials(t.from)}
                </span>
                {t.from}
              </span>
              <span className="settle-arrow">→</span>
              <span className="settle-party">
                <span
                  className="avatar avatar-sm"
                  style={{ background: avatarColor(t.to, people) }}
                >
                  {initials(t.to)}
                </span>
                {t.to}
              </span>
              {t.for && <span className="settle-for">{t.for}</span>}
              <span className="settle-amount">{rupees(t.amount)}</span>
              <a
                href={upiHref}
                className="btn-upi"
                title="Pay via any UPI app"
              >
                Pay via UPI
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
}
