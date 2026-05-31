import { useEffect, useState } from "react";

// There's no real progress signal from a single Claude call, so this is an
// honest *estimate*: the bar eases toward ~95% over the expected ~15s wait and
// only completes when results replace it. Step labels rotate to show life.
const STEPS = [
  "Reading your description…",
  "Identifying who ate what…",
  "Working out the proportional tax…",
  "Balancing the totals…",
  "Almost there…",
];

export default function LoadingProgress() {
  const [pct, setPct] = useState(6);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      // Exponential ease-out, capped at 95% so it never claims to be done early.
      // ~0.04 reaches ~90% around the expected 15s mark.
      setPct((p) => (p >= 95 ? 95 : p + (95 - p) * 0.04));
    }, 200);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(
      () => setStep((s) => Math.min(s + 1, STEPS.length - 1)),
      3000
    );
    return () => clearInterval(id);
  }, []);

  return (
    <div className="loading-progress">
      <div className="progress">
        <div className="progress-bar" style={{ width: `${pct}%` }} />
      </div>
      <div className="progress-step">{STEPS[step]}</div>
    </div>
  );
}
