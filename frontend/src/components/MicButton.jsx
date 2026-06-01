import { useRef, useState } from "react";
import { transcribeAudio } from "../api.js";

// Records a short audio clip with MediaRecorder (reliable across devices,
// including Android) and transcribes it via Groq's Whisper API on the backend.
// Renders nothing where unsupported, so typing always still works.
const supported =
  typeof navigator !== "undefined" &&
  navigator.mediaDevices &&
  typeof navigator.mediaDevices.getUserMedia === "function" &&
  typeof window !== "undefined" &&
  typeof window.MediaRecorder === "function";

const join = (a, b) => (a ? `${a.replace(/\s+$/, "")} ${b}` : b);

export default function MicButton({ value, onChange, disabled }) {
  const [state, setState] = useState("idle"); // idle | recording | transcribing
  const [error, setError] = useState("");
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // Keep the latest textarea value reachable when the clip finishes uploading.
  const valueRef = useRef(value);
  valueRef.current = value;

  if (!supported) return null;

  async function start() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = handleStop;
      recorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch {
      setError("Couldn't access the microphone.");
      setState("idle");
    }
  }

  function stop() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }

  async function handleStop() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    const chunks = chunksRef.current;
    if (!chunks.length) {
      setState("idle");
      return;
    }
    const blob = new Blob(chunks, { type: recorderRef.current?.mimeType || "audio/webm" });

    setState("transcribing");
    try {
      const text = await transcribeAudio(blob);
      if (text) onChange(join(valueRef.current, text));
    } catch (err) {
      setError(err.message || "Transcription failed. Please try again.");
    } finally {
      setState("idle");
    }
  }

  const toggle = () => {
    if (state === "recording") stop();
    else if (state === "idle") start();
  };

  const label =
    state === "recording" ? "Stop" : state === "transcribing" ? "Transcribing…" : "Speak";

  return (
    <>
      <button
        type="button"
        className={state === "recording" ? "mic-btn listening" : "mic-btn"}
        onClick={toggle}
        disabled={disabled || state === "transcribing"}
        aria-label={state === "recording" ? "Stop recording" : "Speak your description"}
        title={state === "recording" ? "Recording… click to stop" : "Speak instead of typing"}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"
            fill="currentColor"
          />
          <path
            d="M19 11a7 7 0 0 1-14 0M12 18v3"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
        {label}
      </button>
      {error && <p className="error" style={{ marginTop: 8, width: "100%" }}>{error}</p>}
    </>
  );
}
