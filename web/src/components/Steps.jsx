// The five steps from the kickoff deck, with the one the user is on highlighted.
export const STEPS = [
  ["Understand", "See the record"],
  ["Connect", "Add the files"],
  ["Detect", "Find the changes"],
  ["Explain", "Why it was flagged"],
  ["Ask", "Use the assistant"],
];

export default function Steps({ current }) {
  return (
    <nav className="flow" aria-label="Where you are in the five steps">
      <ol>
        {STEPS.map(([name, hint], n) => (
          <li key={name} className={name === current ? "on" : ""} aria-current={name === current ? "step" : undefined} title={hint}>
            <span className="num">{n + 1}</span><span className="lbl">{name}</span>
          </li>))}
      </ol>
    </nav>);
}
