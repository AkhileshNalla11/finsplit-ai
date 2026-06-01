import { useRef, useState } from "react";
import { uploadReceipt } from "../api.js";
import LoadingProgress from "./LoadingProgress.jsx";
import MicButton from "./MicButton.jsx";

const RESTAURANT_EXAMPLE =
  "Akhilesh, Kritik, Rujula, Dhruv and Shobhit went to a restaurant. " +
  "Dhruv and Kritik ate only veg (₹1300). Akhilesh, Rujula and Shobhit had both " +
  "veg and non-veg (₹2200). Kritik and Shobhit had beers — ₹400 each. Tax was ₹600.";

const EXAMPLES = [
  {
    label: "Restaurant with mixed orders",
    text: RESTAURANT_EXAMPLE,
  },
  {
    label: "Trip with different rooms",
    text:
      "Four of us — Aditi, Rohan, Meera and Sam — went to Goa for 2 nights. " +
      "Aditi and Rohan shared a deluxe room (₹8000 total). Meera and Sam took a " +
      "standard room (₹5000 total). Dinner on both nights was ₹3200 shared equally. " +
      "Cab from the airport was ₹1800 split among everyone.",
  },
  {
    label: "One person paid for all",
    text:
      "Karan paid the entire bill of ₹4500 for lunch with Neha, Priya and himself. " +
      "Everyone ate roughly the same. Split it equally three ways and tell me what " +
      "Neha and Priya each owe Karan.",
  },
];

export default function DescriptionInput({ value, onChange, onSubmit, loading }) {
  const fileInputRef = useRef(null);
  const [readingReceipt, setReadingReceipt] = useState(false);
  const [receiptError, setReceiptError] = useState("");

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setReceiptError("");
    setReadingReceipt(true);
    try {
      const description = await uploadReceipt(file);
      onChange(description);
    } catch (err) {
      setReceiptError(err.message || "Could not read receipt. Please try again.");
    } finally {
      setReadingReceipt(false);
    }
  }

  const busy = loading || readingReceipt;

  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={busy}
      />

      {loading ? (
        <LoadingProgress />
      ) : (
        <>
          <div className="row mt">
            <button className="btn" onClick={onSubmit} disabled={!value.trim() || busy}>
              Split it
            </button>
            <MicButton value={value} onChange={onChange} disabled={busy} />
            <button
              type="button"
              className="mic-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              title="Upload a receipt photo"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="2" />
              </svg>
              {readingReceipt ? "Reading…" : "Receipt"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
          </div>
          {receiptError && <p className="error" style={{ marginTop: 8 }}>{receiptError}</p>}
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button key={ex.label} className="pill" onClick={() => onChange(ex.text)}>
                {ex.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
