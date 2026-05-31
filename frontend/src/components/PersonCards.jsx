import { rupees, initials, avatarColor } from "../format.js";

export default function PersonCards({ perPerson = {}, people = [] }) {
  const names = people.length ? people : Object.keys(perPerson);
  return (
    <div>
      <div className="section-title">Who owes what</div>
      <div className="cards">
        {names.map((name) => (
          <div className="card" key={name}>
            <div className="avatar" style={{ background: avatarColor(name, names) }}>
              {initials(name)}
            </div>
            <div>
              <div className="name">{name}</div>
              <div className="amount">{rupees(perPerson[name])}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
