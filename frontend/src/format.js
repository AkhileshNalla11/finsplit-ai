// Small shared formatting helpers used across components.

export function rupees(n) {
  const value = Math.round(Number(n) || 0);
  return `₹${value.toLocaleString("en-IN")}`;
}

export function initials(name) {
  const parts = String(name).trim().split(/\s+/);
  return (parts[0]?.[0] || "?").concat(parts[1]?.[0] || "").toUpperCase();
}

// Consistent avatar color per person: hash name to one of 5 palette slots.
export function avatarColor(name, peopleOrder = []) {
  const idx = peopleOrder.indexOf(name);
  const slot = (idx >= 0 ? idx : hash(name)) % 5;
  return `var(--avatar-${slot})`;
}

function hash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}
