import { useState } from "react";
import { createSplit, correctSplit } from "../api.js";
import DescriptionInput from "../components/DescriptionInput.jsx";
import AssumptionsBox from "../components/AssumptionsBox.jsx";
import BreakdownTable from "../components/BreakdownTable.jsx";
import PersonCards from "../components/PersonCards.jsx";
import SettleUp from "../components/SettleUp.jsx";
import CorrectionInput from "../components/CorrectionInput.jsx";

export default function Home() {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [result, setResult] = useState(null);
  const [splitId, setSplitId] = useState(null);

  const [correction, setCorrection] = useState("");
  const [correcting, setCorrecting] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleSplit() {
    setLoading(true);
    setError("");
    try {
      const data = await createSplit(description);
      setResult(data.result);
      setSplitId(data.id);
    } catch (e) {
      setError(e.message || "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCorrect() {
    setCorrecting(true);
    setError("");
    try {
      const data = await correctSplit({
        original_description: description,
        previous_result: result,
        correction,
      });
      setResult(data.result);
      setSplitId(data.id);
      setCorrection("");
      setCopied(false);
    } catch (e) {
      setError(e.message || "Couldn't apply the correction. Try again.");
    } finally {
      setCorrecting(false);
    }
  }

  function reset() {
    setDescription("");
    setResult(null);
    setSplitId(null);
    setCorrection("");
    setError("");
    setCopied(false);
  }

  const shareUrl = splitId ? `${window.location.origin}/split/${splitId}` : null;

  function copyLink() {
    if (!shareUrl) return;
    navigator.clipboard?.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="container">
      <div className="hero">
        <h1 className="brand">
          Fin<span>Split</span> AI
        </h1>
        <p className="tagline">
          Describe the tab your way. We'll split it down to the last cent.
        </p>
      </div>

      {!result ? (
        <>
          <div className="input-card">
            <DescriptionInput
              value={description}
              onChange={setDescription}
              onSubmit={handleSplit}
              loading={loading}
            />
          </div>
          {error && <div className="error">{error}</div>}
        </>
      ) : (
        <>
          <div className="fade-up delay-1">
            <AssumptionsBox oneLiner={result.oneLiner} assumptions={result.assumptions} />
          </div>
          <div className="fade-up delay-2">
            <BreakdownTable items={result.items} totalBill={result.totalBill} />
          </div>
          <div className="fade-up delay-3">
            <PersonCards perPerson={result.perPerson} people={result.people} />
          </div>
          <div className="fade-up delay-4">
            <SettleUp
              settlements={result.settlements}
              settlementsDetailed={result.settlementsDetailed}
              paidBy={result.paidBy}
              people={result.people}
            />
          </div>

          <div className="fade-up delay-5">
            <CorrectionInput
              value={correction}
              onChange={setCorrection}
              onSubmit={handleCorrect}
              loading={correcting}
            />
            {error && <div className="error">{error}</div>}

            <div className="share">
              {shareUrl ? (
                <>
                  <span className="url">{shareUrl}</span>
                  <button className="btn btn-secondary" onClick={copyLink}>
                    {copied ? "Copied!" : "Copy link"}
                  </button>
                </>
              ) : (
                <span className="url">Sharing unavailable — storage is offline.</span>
              )}
              <button className="btn btn-secondary" onClick={reset}>
                New split
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
