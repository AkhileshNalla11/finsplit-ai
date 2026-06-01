import LoadingProgress from "./LoadingProgress.jsx";
import MicButton from "./MicButton.jsx";

export default function CorrectionInput({ value, onChange, onSubmit, loading }) {
  return (
    <div className="correction">
      <label htmlFor="correction">Something wrong? Correct it in plain English</label>
      <textarea
        id="correction"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. Dhruv didn't have any beer, and split the tax equally instead."
        disabled={loading}
        style={{ minHeight: "90px" }}
      />
      {loading ? (
        <LoadingProgress />
      ) : (
        <div className="row mt">
          <button className="btn" onClick={onSubmit} disabled={!value.trim()}>
            Recalculate
          </button>
          <MicButton value={value} onChange={onChange} disabled={loading} />
        </div>
      )}
    </div>
  );
}
