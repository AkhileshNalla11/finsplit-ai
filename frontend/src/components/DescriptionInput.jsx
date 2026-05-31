import LoadingProgress from "./LoadingProgress.jsx";

const PLACEHOLDER =
  "Akhilesh, Kritik, Rujula, Dhruv and Shobhit went to a restaurant. " +
  "Dhruv and Kritik ate only veg (₹1300). Akhilesh, Rujula and Shobhit had both " +
  "veg and non-veg (₹2200). Kritik and Shobhit had beers — ₹400 each. Tax was ₹600.";

const EXAMPLES = [
  {
    label: "Restaurant with mixed orders",
    text: PLACEHOLDER,
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
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={PLACEHOLDER}
        disabled={loading}
      />

      {loading ? (
        <LoadingProgress />
      ) : (
        <>
          <div className="row mt">
            <button className="btn" onClick={onSubmit} disabled={!value.trim()}>
              Split it
            </button>
          </div>
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
