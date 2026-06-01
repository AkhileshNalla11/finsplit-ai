import { useEffect, useRef, useState } from "react";

// Browser-native speech-to-text (Web Speech API). Free, on-device, no backend.
// Renders nothing where unsupported (e.g. Firefox), so typing always still works.
const SpeechRecognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function MicButton({ value, onChange, disabled }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const baseRef = useRef(""); // textarea text captured when recording started
  const finalRef = useRef(""); // finalized transcript accumulated this session

  // Keep the latest value/onChange reachable inside the recognition callbacks.
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  valueRef.current = value;
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!SpeechRecognition) return undefined;

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-IN";

    rec.onresult = (event) => {
      // Only process results new to this event; finalized ones are accumulated
      // once into finalRef so a phrase is never concatenated more than once.
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalRef.current += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      const transcript = (finalRef.current + interim).trim();
      const base = baseRef.current;
      const joined = base ? `${base.replace(/\s+$/, "")} ${transcript}` : transcript;
      onChangeRef.current(joined);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);

    recognitionRef.current = rec;
    return () => {
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
      rec.stop();
      return;
    }
    baseRef.current = valueRef.current || "";
    finalRef.current = "";
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
