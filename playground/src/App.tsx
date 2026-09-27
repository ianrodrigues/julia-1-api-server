import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ask, cleanQuestion, curlCommand, questionKey, requestBody, type Outcome } from "./api";
import { Answers, AnswersSkeleton, type Run } from "./Answers";
import { PlusIcon, QuestionCard, TypeIcon } from "./QuestionCard";
import { BLANK, SCENARIOS } from "./scenarios";
import { LIMITS, TYPE_LABELS, type Question, type QuestionType, type Scenario } from "./types";

let nextId = 0;
const newId = () => `question-${++nextId}`;
const withIds = (scenario: Scenario): Question[] => scenario.questions.map((q) => ({ ...q, id: newId(), options: [...q.options] }));

const KEY_STORAGE = "julia-1-playground:api-key";
function loadKey() {
  try {
    return localStorage.getItem(KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}
function saveKey(key: string) {
  try {
    if (key) localStorage.setItem(KEY_STORAGE, key);
    else localStorage.removeItem(KEY_STORAGE);
  } catch {
    // Storage can be blocked; the key then lasts for this visit only.
  }
}

/** The first thing stopping a run, phrased as what to do next. */
function firstProblem(text: string, questions: Question[]): string | null {
  if (!text.trim()) return "Add some text for Julia-1 to read.";
  for (const [index, raw] of questions.entries()) {
    const question = cleanQuestion(raw);
    const name = `Question ${index + 1}`;
    if (!question.instructions) return `${name} needs a question.`;
    if (question.type === "noul") continue;
    if (question.options.length < 2) return `${name} needs at least two ${question.type === "choice" ? "options" : "levels"}.`;
    if (new Set(question.options.map((o) => o.toLowerCase())).size !== question.options.length)
      return `${name} lists the same ${question.type === "choice" ? "option" : "level"} twice.`;
  }
  return null;
}

export function App() {
  const [scenarioId, setScenarioId] = useState(SCENARIOS[0]!.id);
  const [text, setText] = useState(SCENARIOS[0]!.state);
  const [questions, setQuestions] = useState<Question[]>(() => withIds(SCENARIOS[0]!));
  const [focus, setFocus] = useState<{ question: number; option: number | null } | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [runSignature, setRunSignature] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<Extract<Outcome, { ok: false }> | null>(null);
  const [apiKey, setApiKey] = useState(loadKey);
  const [needsKey, setNeedsKey] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const answersRef = useRef<HTMLDivElement>(null);
  const questionInputs = useRef<HTMLDivElement>(null);

  const body = useMemo(() => requestBody(text.trim(), questions), [text, questions]);
  const signature = JSON.stringify(body);
  const problem = firstProblem(text, questions);
  const stale = run !== null && signature !== runSignature;

  const loadScenario = (scenario: Scenario) => {
    setScenarioId(scenario.id);
    setText(scenario.state);
    setQuestions(withIds(scenario));
    setRun(null);
    setError(null);
  };

  const updateQuestion = (index: number, next: Question) =>
    setQuestions((current) => current.map((question, i) => (i === index ? next : question)));

  const addQuestion = (type: QuestionType) => {
    if (questions.length >= LIMITS.questions) return;
    setQuestions((current) => [...current, { id: newId(), type, instructions: "", options: type === "noul" ? [] : ["", ""] }]);
    setFocus({ question: questions.length, option: null });
  };

  // Focus a newly added question's text field once it has rendered.
  useEffect(() => {
    if (focus?.option !== null || focus === null) return;
    const inputs = questionInputs.current?.querySelectorAll<HTMLInputElement>(".question-input");
    inputs?.[focus.question]?.focus();
    setFocus(null);
  }, [focus]);

  const submit = useCallback(async () => {
    if (problem || running) return;
    setRunning(true);
    setError(null);
    const snapshot = questions.map(cleanQuestion);
    const outcome = await ask(body, apiKey);
    setRunning(false);
    if (!outcome.ok) {
      setError(outcome);
      if (outcome.kind === "auth") setNeedsKey(true);
      return;
    }
    setRun({
      questions: snapshot,
      answers: snapshot.map((_, index) => outcome.response.answers[questionKey(index)]),
      serverMs: outcome.serverMs,
      totalMs: outcome.totalMs,
      tokens: outcome.response.usage.input_tokens,
    });
    setRunSignature(JSON.stringify(body));
    // On narrow screens the answers sit below the editor; bring them into view.
    if (window.matchMedia("(max-width: 959px)").matches) {
      requestAnimationFrame(() => answersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }, [problem, running, questions, body, apiKey]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        void submit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [submit]);

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(curlCommand(body, window.location.origin));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

  return (
    <div className="page">
      <header className="topbar">
        <a className="wordmark" href="/playground" aria-label="Julia-1 Playground home">
          <span className="wordmark-name">Julia-1</span>
          <span className="wordmark-tag">playground</span>
        </a>
        <nav className="topnav" aria-label="Links">
          <a href="/docs">API docs</a>
          <a href="https://github.com/ianrodrigues/julia-1-api-server" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>

      <section className="hero">
        <h1>
          Ask a question about any text.
          <br />
          Get a decision, <em>with the odds.</em>
        </h1>
        <p className="hero-lede">
          Julia-1 doesn't chat or write essays. It reads your text, answers each of your questions in one pass, and
          tells you how sure it is. Pick an example below, or write your own.
        </p>
      </section>

      <section className="step step--scenarios" aria-labelledby="scenarios-title">
        <h2 id="scenarios-title" className="step-title">
          <span className="step-number">1</span> Pick a scenario
        </h2>
        <div className="scenarios" role="list">
          {[...SCENARIOS, BLANK].map((scenario, i) => (
            <button
              key={scenario.id}
              type="button"
              role="listitem"
              aria-pressed={scenario.id === scenarioId}
              className={`scenario ${scenario.id === BLANK.id ? "scenario--blank" : ""}`}
              style={{ "--i": i } as React.CSSProperties}
              onClick={() => loadScenario(scenario)}
            >
              <span className="scenario-title">{scenario.title}</span>
              <span className="scenario-blurb">{scenario.blurb}</span>
            </button>
          ))}
        </div>
      </section>

      <div className="workspace">
        <div className="editor">
          <section className="step" aria-labelledby="text-title">
            <h2 id="text-title" className="step-title">
              <span className="step-number">2</span> The text Julia-1 reads
            </h2>
            <div className="text-field">
              <textarea
                aria-labelledby="text-title"
                value={text}
                maxLength={LIMITS.text}
                placeholder="Paste an email, a review, a chat message, anything…"
                rows={6}
                onChange={(event) => setText(event.target.value)}
              />
              <span className="text-count">{text.length.toLocaleString()} characters</span>
            </div>
          </section>

          <section className="step" aria-labelledby="questions-title">
            <h2 id="questions-title" className="step-title">
              <span className="step-number">3</span> Your questions
            </h2>
            <div className="questions" ref={questionInputs}>
              {questions.map((question, index) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  index={index}
                  canRemove={questions.length > 1}
                  onChange={(next) => updateQuestion(index, next)}
                  onRemove={() => setQuestions((current) => current.filter((_, i) => i !== index))}
                  focusOption={focus?.question === index ? focus.option : null}
                  onFocusOption={(option) => setFocus(option === null ? null : { question: index, option })}
                />
              ))}
            </div>
            {questions.length < LIMITS.questions ? (
              <div className="add-question">
                <span className="add-question-label">
                  <PlusIcon /> Add a question
                </span>
                {(Object.keys(TYPE_LABELS) as QuestionType[]).map((type) => (
                  <button key={type} type="button" className="add-question-type" onClick={() => addQuestion(type)} title={TYPE_LABELS[type].hint}>
                    <TypeIcon type={type} /> {TYPE_LABELS[type].name}
                  </button>
                ))}
              </div>
            ) : (
              <p className="question-note">That's the playground's limit of {LIMITS.questions} questions.</p>
            )}
          </section>

          <div className="runbar">
            {needsKey && (
              <label className="key-field">
                <span>API key</span>
                <input
                  type="password"
                  value={apiKey}
                  autoComplete="off"
                  placeholder="Paste the key for this server"
                  onChange={(event) => {
                    setApiKey(event.target.value);
                    saveKey(event.target.value.trim());
                  }}
                />
              </label>
            )}
            <button type="button" className="run" onClick={() => void submit()} disabled={Boolean(problem) || running}>
              {running ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Thinking…
                </>
              ) : (
                <>
                  Ask Julia-1 <kbd>{isMac ? "⌘" : "Ctrl"} ↵</kbd>
                </>
              )}
            </button>
            <p className="runbar-hint" role="status">
              {problem ?? (error ? "" : `${questions.length} question${questions.length === 1 ? "" : "s"}, answered together in one request.`)}
            </p>
          </div>
        </div>

        <aside className="results" ref={answersRef} aria-labelledby="answers-title" aria-live="polite">
          <h2 id="answers-title" className="step-title">
            <span className="step-number">4</span> Julia-1's answers
          </h2>
          {error && (
            <div className={`alert alert--${error.kind}`} role="alert">
              {error.message}
            </div>
          )}
          {running ? (
            <AnswersSkeleton count={questions.length} />
          ) : run ? (
            <Answers run={run} stale={stale} />
          ) : (
            <EmptyAnswers />
          )}

          <div className="code">
            <button type="button" className="code-toggle" aria-expanded={showCode} onClick={() => setShowCode((shown) => !shown)}>
              {showCode ? "Hide" : "Show"} the API request
            </button>
            {showCode && (
              <div className="code-panel">
                <button type="button" className="code-copy" onClick={() => void copyCode()}>
                  {copied ? "Copied" : "Copy"}
                </button>
                <pre>
                  <code>{curlCommand(body, window.location.origin)}</code>
                </pre>
                <p className="code-note">
                  Same request format as TypeSafe's Jev API. See the <a href="/docs">API docs</a>.
                </p>
              </div>
            )}
          </div>
        </aside>
      </div>

      <footer className="footer">
        <span>
          Julia-1 by{" "}
          <a href="https://huggingface.co/SupersonicLabs/Julia-1" target="_blank" rel="noreferrer">
            Supersonic Labs
          </a>
          , served by{" "}
          <a href="https://github.com/ianrodrigues/julia-1-api-server" target="_blank" rel="noreferrer">
            julia-1-api-server
          </a>
          .
        </span>
        <span>Answers come from a small model and can be wrong. Don't paste anything private.</span>
      </footer>
    </div>
  );
}

const EMPTY_TYPES: [QuestionType, string][] = [
  ["choice", "The best option, with the odds for every option."],
  ["score", "Where it lands on your scale, even between two levels."],
  ["noul", "The chance that the answer is yes."],
];

function EmptyAnswers() {
  return (
    <div className="empty">
      <p className="empty-title">Answers appear here.</p>
      <p>Press <strong>Ask Julia-1</strong> to run the questions. Each type answers differently:</p>
      <ul className="empty-types">
        {EMPTY_TYPES.map(([type, description]) => (
          <li key={type}>
            <span className="empty-icon">
              <TypeIcon type={type} />
            </span>
            <span>
              <strong>{TYPE_LABELS[type].name}.</strong> {description}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
