import { rupees } from "../format.js";

function SharedBy({ sharedBy = [], gifted = [] }) {
  const giftedSet = new Set(gifted);
  return sharedBy.map((name, i) => (
    <span key={name}>
      {i > 0 && ", "}
      {name}
      {giftedSet.has(name) && <span className="gifted-tag"> (gifted)</span>}
    </span>
  ));
}

export default function BreakdownTable({ items = [], totalBill }) {
  return (
    <div>
      <div className="section-title">Breakdown</div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Shared by</th>
              <th className="num">Per head</th>
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i}>
                <td>{item.label}</td>
                <td className="shared-by">
                  <SharedBy sharedBy={item.sharedBy} gifted={item.gifted} />
                </td>
                <td className="num">{rupees(item.perHead)}</td>
                <td className="num">{rupees(item.total)}</td>
              </tr>
            ))}
            <tr className="total-row">
              <td colSpan={3}>Total bill</td>
              <td className="num">{rupees(totalBill)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
