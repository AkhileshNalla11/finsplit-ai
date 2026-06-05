import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchSplit } from "../api.js";
import AssumptionsBox from "../components/AssumptionsBox.jsx";
import BreakdownTable from "../components/BreakdownTable.jsx";
import PersonCards from "../components/PersonCards.jsx";
import SettleUp from "../components/SettleUp.jsx";

export default function SplitView() {
  const { id } = useParams();
  const [state, setState] = useState({ loading: true, result: null });

  useEffect(() => {
    let active = true;
    fetchSplit(id)
      .then((data) => active && setState({ loading: false, result: data?.result || null }))
      .catch(() => active && setState({ loading: false, result: null }));
    return () => {
      active = false;
    };
  }, [id]);

  if (state.loading) {
    return (
      <div className="container">
        <div className="loading">
          <div className="spinner" />
          Loading split...
        </div>
      </div>
    );
  }

  if (!state.result) {
    return (
      <div className="container center">
        <p>This split link has expired or doesn't exist.</p>
        <Link className="link" to="/">
          Create a new split →
        </Link>
      </div>
    );
  }

  const r = state.result;
  return (
    <div className="container">
      <div className="hero" style={{ paddingBottom: 16 }}>
        <h1 className="brand">
          Fin<span>Split</span> AI
        </h1>
        <p className="tagline">A shared split.</p>
      </div>

      <AssumptionsBox oneLiner={r.oneLiner} assumptions={r.assumptions} />
      <BreakdownTable items={r.items} totalBill={r.totalBill} />
      <PersonCards perPerson={r.perPerson} people={r.people} />
      <SettleUp
        settlements={r.settlements}
        settlementsDetailed={r.settlementsDetailed}
        paidBy={r.paidBy}
        people={r.people}
        splitId={id}
      />

      <div className="footer">
        Split by{" "}
        <Link to="/">FinSplit AI</Link>
      </div>
    </div>
  );
}
