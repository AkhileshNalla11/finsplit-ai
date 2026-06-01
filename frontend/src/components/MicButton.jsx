import { useEffect, useRef, useState } from "react";

// Browser-native speech-to-text (Web Speech API). Free, on-device, no backend.
// Renders nothing where unsupported (e.g. Firefox), so typing always still works.
const SpeechRecognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function MicButton({ value, onChange, disabled }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const baseRef = useRef(""); // committed text so far; grows as utterances finalize
  const shouldListenRef = useRef(false); // true while the user wants to keep dictating

  // Keep the latest value/onChange reachable inside the recognition callbacks.
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  valueRef.current = value;
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!SpeechRecognition) return undefined;

    const rec = new SpeechRecognition();
    // One finalized utterance per result, no interim snapshots. Mobile Chrome
    // (Android) re-delivers growing interim snapshots as separate finalized
    // results, which duplicates text — disabling interim avoids that entirely.
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = "en-IN";

    rec.onresult = (event) => {
      // Append this utterance's finalized transcript exactly once, then commit
      // it into baseRef so the next utterance appends after it.
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      transcript = transcript.trim();
      if (!transcript) return;
      const base = baseRef.current;
      const next = base ? `${base.replace(/\s+$/, "")} ${transcript}` : transcript;
      baseRef.current = next;
      onChangeRef.current(next);
    };

    rec.onend = () => {
      // Recognition stops after each utterance (and on Android after pauses);
      // restart while the user still wants to dictate.
      if (shouldListenRef.current) {
        try {
          rec.start();
        } catch {
          /* start() throws if it hasn't fully stopped yet — ignore */
        }
      } else {
        setListening(false);
      }
    };

    rec.onerror = (e) => {
      // Permission/service failures are fatal; transient ones (no-speech,
      // aborted) fall through to onend, which restarts if still listening.
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        shouldListenRef.current = false;
        setListening(false);
      }
    };

    recognitionRef.current = rec;
    return () => {
      shouldListenRef.current = false;
      rec.onresult = rec.onend = rec.onerror = null;
      try {
        rec.abort();
      } catch {
        /* already stopped */
      }
    };
  }, []);

  if (!SpeechRecognition) return null;

  const toggle = () => {
    const rec = recognitionRef.current;
    if (!rec) return;
    if (listening) {
      shouldListenRef.current = false;
      rec.stop();
      return;
    }
    baseRef.current = valueRef.current || "";
    shouldListenRef.current = true;
    try {
      rec.start();
      setListening(true);
    } catch {
      /* start() throws if already started — ignore */
    }
  };

  return (
    <button
      type="button"
      className={listening ? "mic-btn listening" : "mic-btn"}
      onClick={toggle}
      disabled={disabled}
      aria-label={listening ? "Stop voice input" : "Speak your description"}
      title={listening ? "Listening… click to stop" : "Speak instead of typing"}
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
      {listening ? "Listening…" : "Speak"}
    </button>
  );
}
