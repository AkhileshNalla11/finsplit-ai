import { rupees, initials, avatarColor } from "../format.js";
import { removeFromHistory, timeAgo } from "../utils/splitHistory.js";

export default function SplitHistory({ history, onRestore, onHistoryChange }) {
  if (!history.length) return null;

  function handleDelete(e, id) {
    e.stopPropagation();
    removeFromHistory(id);
    onHistoryChange();
  }

  return (
    <div className="history">
      <div className="history-header">
        <span className="section-title" style={{ marginBottom: 0 }}>Recent splits</span>
      </div>
      <div className="history-list">
        {history.map((entry) => (
          <div
            className="history-card"
            key={entry.id}
            onClick={() => onRestore(entry)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onRestore(entry)}
          >
            <div className="history-card-top">
              <span className="history-oneliner">{entry.oneLiner}</span>
              <span className="history-amount">{rupees(entry.totalBill)}</span>
            </div>
            <div className="history-card-bottom">
              <span className="history-people">
                {(entry.people || []).slice(0, 5).map((name) => (
                  <span
                    key={name}
                    className="history-avatar"
                    style={{ background: avatarColor(name, entry.people) }}
                    title={name}
                  >
                    {initials(name)}
                  </span>
                ))}
                {entry.people?.length > 5 && (
                  <span className="history-more">+{entry.people.length - 5}</span>
                )}
              </span>
              <span className="history-meta">{timeAgo(entry.createdAt)}</span>
            </div>
            <button
              className="history-delete"
              onClick={(e) => handleDelete(e, entry.id)}
              aria-label="Remove from history"
              title="Remove"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
