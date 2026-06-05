const HISTORY_KEY = "finsplit_history";
const MAX_ENTRIES = 10;

export function saveToHistory({ id, description, result, shareUrl }) {
  const history = getHistory();
  const entry = {
    id,
    description: description || "",
    oneLiner: result.oneLiner || "Bill split",
    totalBill: result.totalBill || 0,
    people: result.people || Object.keys(result.perPerson || {}),
    createdAt: Date.now(),
    shareUrl: shareUrl || null,
    result,
  };
  const filtered = history.filter((h) => h.id !== id);
  const updated = [entry, ...filtered].slice(0, MAX_ENTRIES);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch {
    // Storage quota exceeded — trim and retry once
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated.slice(0, 3)));
    } catch { /* ignore */ }
  }
}

export function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

export function removeFromHistory(id) {
  const updated = getHistory().filter((h) => h.id !== id);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch { /* ignore */ }
}

// ── Mark-as-paid helpers ─────────────────────────────────────────────────────

function paidKey(splitId) {
  return `finsplit_paid_${splitId}`;
}

export function loadPaidSet(splitId) {
  if (!splitId) return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(paidKey(splitId)) || "[]"));
  } catch {
    return new Set();
  }
}

export function savePaidSet(splitId, paid) {
  if (!splitId) return;
  try {
    localStorage.setItem(paidKey(splitId), JSON.stringify([...paid]));
  } catch { /* ignore */ }
}

export function settlementKey(t) {
  return `${t.from}→${t.to}→${t.amount}`;
}

// Simple relative-time formatter
export function timeAgo(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
