const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function createSplit(description) {
  return post("/api/split", { description });
}

export function correctSplit({ original_description, previous_result, correction }) {
  return post("/api/correct", { original_description, previous_result, correction });
}

export async function uploadReceipt(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/read-receipt`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  const data = await res.json();
  return data.description;
}

export async function transcribeAudio(blob) {
  const form = new FormData();
  const ext = blob.type.includes("ogg")
    ? "ogg"
    : blob.type.includes("mp4")
      ? "mp4"
      : "webm";
  form.append("file", blob, `audio.${ext}`);
  const res = await fetch(`${BASE}/api/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  const data = await res.json();
  return data.text;
}

export async function fetchSplit(id) {
  const res = await fetch(`${BASE}/api/split/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}
