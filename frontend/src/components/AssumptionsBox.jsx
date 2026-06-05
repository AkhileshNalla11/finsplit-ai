export default function AssumptionsBox({ oneLiner, assumptions = [] }) {
  return (
    <div className="assumptions">
      <h2>How we read it</h2>
      {oneLiner && <p className="one-liner">{oneLiner}</p>}
      {assumptions.length > 0 && (
        <ul>
          {assumptions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
