import { useEffect, useRef, useState } from "react";

// Browser-native speech-to-text (Web Speech API). Free, on-device, no backend.
// Renders nothing where unsupported (e.g. Firefox), so typing always still works.
const SpeechRecognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

// Join committed text with a new chunk, collapsing trailing whitespace.
const join = (a, b) => (a ? `${a.replace(/\s+$/, "")} ${b}` : b);

export default function MicButton({ value, onChange, disabled }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  // committed: text finalized so far (seeded with the textarea value at start).
  // tail: the current utterance's latest (longest) transcript snapshot.
  // tailLen: length of the previous tail, to detect when a new utterance begins.
  const committedRef = useRef("");
  const tailRef = useRef("");
  const tailLenRef = useRef(0);
  const shouldListenRef = useRef(false); // true while the user wants to keep dictating

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
      // The results list can contain growing PREFIX snapshots of the same phrase
      // (notably on Android Chrome). Concatenating them duplicates text, so we
      // take ONLY the last entry — the most complete snapshot — and never glue
      // the prefixes together.
      const results = event.results;
      const tail = results[results.length - 1][0].transcript.trim();

      // A shorter tail than before means a new utterance started: commit the
      // previous phrase before tracking the new one.
      if (tail.length < tailLenRef.current && tailRef.current) {
        committedRef.current = join(committedRef.current, tailRef.current);
      }
      tailRef.current = tail;
      tailLenRef.current = tail.length;

      onChangeRef.current(join(committedRef.current, tail));
    };

    rec.onend = () => {
      // Commit the in-flight phrase so it survives a restart, then keep going
      // while the user is still dictating (Android stops after each pause).
      if (tailRef.current) {
        committedRef.current = join(committedRef.current, tailRef.current);
        tailRef.current = "";
        tailLenRef.current = 0;
      }
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
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        shouldListenRef.current = false;
        setListening(false);
      }
      // Transient errors (no-speech, aborted) fall through to onend.
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
    committedRef.current = valueRef.current || "";
    tailRef.current = "";
    tailLenRef.current = 0;
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
