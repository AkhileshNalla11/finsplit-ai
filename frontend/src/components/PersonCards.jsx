import { rupees, initials, avatarColor } from "../format.js";

export default function PersonCards({ perPerson = {}, people = [] }) {
  const names = people.length ? people : Object.keys(perPerson);
  return (
    <div>
      <div className="section-title">Who owes what</div>
      <div className="cards">
        {names.map((name) => {
          const color = avatarColor(name, names);
          return (
            <div
              className="card"
              key={name}
              style={{ "--card-accent": color }}
            >
              <div className="avatar" style={{ background: color }}>
                {initials(name)}
              </div>
              <div>
                <div className="name">{name}</div>
                <div className="amount">{rupees(perPerson[name])}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
