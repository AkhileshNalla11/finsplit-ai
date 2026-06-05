import { useState } from "react";
import { createSplit, correctSplit } from "../api.js";
import DescriptionInput from "../components/DescriptionInput.jsx";
import AssumptionsBox from "../components/AssumptionsBox.jsx";
import BreakdownTable from "../components/BreakdownTable.jsx";
import PersonCards from "../components/PersonCards.jsx";
import SettleUp from "../components/SettleUp.jsx";
import CorrectionInput from "../components/CorrectionInput.jsx";
import SplitHistory from "../components/SplitHistory.jsx";
import { saveToHistory, getHistory } from "../utils/splitHistory.js";

function WhatsAppIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  );
}

export default function Home() {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [result, setResult] = useState(null);
  const [splitId, setSplitId] = useState(null);

  const [correction, setCorrection] = useState("");
  const [correcting, setCorrecting] = useState(false);
  const [copied, setCopied] = useState(false);

  const [history, setHistory] = useState(() => getHistory());

  function refreshHistory() {
    setHistory(getHistory());
  }

  async function handleSplit() {
    setLoading(true);
    setError("");
    try {
      const data = await createSplit(description);
      setResult(data.result);
      setSplitId(data.id);
      const url = data.id ? `${window.location.origin}/split/${data.id}` : null;
      saveToHistory({ id: data.id, description, result: data.result, shareUrl: url });
      refreshHistory();
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
      const url = data.id ? `${window.location.origin}/split/${data.id}` : null;
      saveToHistory({ id: data.id, description, result: data.result, shareUrl: url });
      refreshHistory();
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

  function handleRestore(entry) {
    setDescription(entry.description || "");
    setResult(entry.result);
    setSplitId(entry.id);
    setCopied(false);
    setCorrection("");
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const shareUrl = splitId ? `${window.location.origin}/split/${splitId}` : null;

  function copyLink() {
    if (!shareUrl) return;
    navigator.clipboard?.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function buildWhatsAppText() {
    const lines = ["💰 *FinSplit result*"];
    (result.settlements || []).forEach((s) => {
      lines.push(`${s.from} owes ${s.to} ₹${s.amount}`);
    });
    lines.push(`Total bill: ₹${result.totalBill}`);
    if (shareUrl) lines.push(`\nFull breakdown 👉 ${shareUrl}`);
    return encodeURIComponent(lines.join("\n"));
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
          <div className="how-it-works">
            <div className="step"><span>📝</span> Describe the bill</div>
            <span className="step-arrow">→</span>
            <div className="step"><span>✨</span> We split it fairly</div>
            <span className="step-arrow">→</span>
            <div className="step"><span>📲</span> Share with the group</div>
          </div>
          <div className="input-card">
            <DescriptionInput
              value={description}
              onChange={setDescription}
              onSubmit={handleSplit}
              loading={loading}
            />
          </div>
          {error && <div className="error">{error}</div>}
          <SplitHistory
            history={history}
            onRestore={handleRestore}
            onHistoryChange={refreshHistory}
          />
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
            <PersonCards
              perPerson={result.perPerson}
              people={result.people}
              totalBill={result.totalBill}
            />
          </div>
          <div className="fade-up delay-4">
            <SettleUp
              settlements={result.settlements}
              settlementsDetailed={result.settlementsDetailed}
              paidBy={result.paidBy}
              people={result.people}
              splitId={splitId}
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

            {result.settlements?.length > 0 && (
              <a
                href={`https://wa.me/?text=${buildWhatsAppText()}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-wa"
              >
                <WhatsAppIcon /> Share on WhatsApp
              </a>
            )}

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
