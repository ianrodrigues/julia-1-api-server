import type { Answer, ChoiceAnswer, NoulAnswer, Question, ScoreAnswer } from "./types";
import { TypeIcon } from "./QuestionCard";

export interface Run {
  questions: Question[];
  answers: (Answer | undefined)[];
  serverMs: number | null;
  totalMs: number;
  tokens: number;
}

const percent = (value: number) => `${Math.round(value * 100)}%`;
const style = (vars: Record<string, string | number>) => vars as React.CSSProperties;

function certainty(confidence: number) {
  if (confidence >= 0.75) return { label: "Very sure", tone: "high" };
  if (confidence >= 0.4) return { label: "Fairly sure", tone: "mid" };
  return { label: "Not sure", tone: "low" };
}

function Certainty({ confidence }: { confidence: number }) {
  const { label, tone } = certainty(confidence);
  return (
    <span className={`certainty certainty--${tone}`} title={`Confidence ${confidence.toFixed(2)} out of 1`}>
      <span className="certainty-dots" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {label}
    </span>
  );
}

export function Answers({ run, stale }: { run: Run; stale: boolean }) {
  return (
    <div className={`answers ${stale ? "answers--stale" : ""}`}>
      <div className="stats" aria-label="Request statistics">
        <Stat value={run.serverMs === null ? "—" : `${Math.round(run.serverMs)} ms`} label="thinking time" accent />
        <Stat value={`${Math.round(run.totalMs)} ms`} label="round trip" />
        <Stat value={run.tokens.toLocaleString()} label="tokens read" />
      </div>
      {stale && <p className="stale-note">You've edited since this run. Ask again to refresh.</p>}
      {run.questions.map((question, index) => {
        const answer = run.answers[index];
        return (
          <section key={question.id} className="answer" style={style({ "--i": index })} aria-label={`Answer to question ${index + 1}`}>
            <p className="answer-question">
              <span className="answer-type">
                <TypeIcon type={question.type} />
              </span>
              <span>
                <span className="answer-number">Q{index + 1}</span> {question.instructions}
              </span>
            </p>
            {answer?.type === "choice" && <ChoiceResult answer={answer} />}
            {answer?.type === "score" && <ScoreResult answer={answer} levels={question.options} />}
            {answer?.type === "noul" && <NoulResult answer={answer} />}
          </section>
        );
      })}
    </div>
  );
}

function Stat({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className={`stat ${accent ? "stat--accent" : ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function Bars({ entries, winner }: { entries: [string, number][]; winner?: string }) {
  return (
    <ul className="bars">
      {entries.map(([label, probability], i) => (
        <li key={label} className={`bar ${label === winner ? "bar--winner" : ""}`} style={style({ "--i": i })}>
          <span className="bar-label">{label}</span>
          <span className="bar-track" aria-hidden="true">
            <span className="bar-fill" style={style({ "--w": percent(probability) })} />
          </span>
          <span className="bar-value">{percent(probability)}</span>
        </li>
      ))}
    </ul>
  );
}

function ChoiceResult({ answer }: { answer: ChoiceAnswer }) {
  const entries = Object.entries(answer.probabilities).sort((a, b) => b[1] - a[1]);
  return (
    <>
      <div className="verdict">
        <span className="verdict-label">Answer</span>
        <strong className="verdict-value">{answer.choice}</strong>
        <Certainty confidence={answer.confidence} />
      </div>
      <Bars entries={entries} winner={answer.choice} />
    </>
  );
}

function ScoreResult({ answer, levels }: { answer: ScoreAnswer; levels: string[] }) {
  const top = levels.length - 1;
  const nearest = levels[Math.round(answer.score)] ?? "";
  const position = top > 0 ? answer.score / top : 0;
  const entries = levels.map((level, i): [string, number] => [level, answer.probabilities[String(i)] ?? 0]);
  return (
    <>
      <div className="verdict">
        <span className="verdict-label">Closest to</span>
        <strong className="verdict-value">{nearest}</strong>
        <Certainty confidence={answer.confidence} />
      </div>
      <div className="scale" aria-label={`Score ${answer.score.toFixed(2)} on a scale from 1 to ${levels.length}`}>
        <div className="scale-track">
          {levels.map((level, i) => (
            <span key={level + i} className="scale-tick" style={style({ "--at": top > 0 ? i / top : 0 })} />
          ))}
          <span className="scale-marker" style={style({ "--at": position })}>
            <span className="scale-marker-value">{(answer.score + 1).toFixed(1)}</span>
          </span>
        </div>
        <div className="scale-labels" aria-hidden="true">
          <span>{levels[0]}</span>
          <span>{levels[top]}</span>
        </div>
      </div>
      <Bars entries={entries} winner={nearest} />
    </>
  );
}

function NoulResult({ answer }: { answer: NoulAnswer }) {
  const yes = answer.noul;
  const verdict = yes >= 0.65 ? "Yes" : yes <= 0.35 ? "No" : "Unclear";
  return (
    <>
      <div className="verdict">
        <span className="verdict-label">Answer</span>
        <strong className={`verdict-value verdict-value--${verdict.toLowerCase()}`}>{verdict}</strong>
        <Certainty confidence={Math.abs(yes - 0.5) * 2} />
      </div>
      <div className="split" aria-label={`${percent(yes)} chance of yes`}>
        <div className="split-track" aria-hidden="true">
          <span className="split-yes" style={style({ "--w": percent(yes) })} />
          <span className="split-mid" />
        </div>
        <div className="split-labels">
          <span>
            <strong>{percent(yes)}</strong> yes
          </span>
          <span>
            <strong>{percent(1 - yes)}</strong> no
          </span>
        </div>
      </div>
    </>
  );
}

export function AnswersSkeleton({ count }: { count: number }) {
  return (
    <div className="answers" aria-busy="true" aria-label="Julia-1 is thinking">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="answer answer--skeleton" style={style({ "--i": i })}>
          <span className="skeleton skeleton--line" />
          <span className="skeleton skeleton--big" />
          <span className="skeleton skeleton--bar" />
          <span className="skeleton skeleton--bar" />
        </div>
      ))}
    </div>
  );
}
