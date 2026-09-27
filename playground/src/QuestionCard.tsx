import { useEffect, useRef } from "react";
import { LIMITS, TYPE_LABELS, type Question, type QuestionType } from "./types";

const PLACEHOLDERS: Record<QuestionType, string> = {
  choice: "e.g. Which team should handle this?",
  score: "e.g. How urgent is this?",
  noul: "e.g. Is the customer asking for a refund?",
};

interface Props {
  question: Question;
  index: number;
  canRemove: boolean;
  onChange: (question: Question) => void;
  onRemove: () => void;
  /** Index of the option to focus after it was added; consumed on render. */
  focusOption: number | null;
  onFocusOption: (index: number | null) => void;
}

export function QuestionCard({ question, index, canRemove, onChange, onRemove, focusOption, onFocusOption }: Props) {
  const optionRefs = useRef<(HTMLInputElement | null)[]>([]);
  const { type, instructions, options } = question;

  useEffect(() => {
    if (focusOption === null) return;
    optionRefs.current[focusOption]?.focus();
    onFocusOption(null);
  }, [focusOption, onFocusOption]);

  const setType = (next: QuestionType) => {
    const padded = next === "noul" ? options : [...options, "", ""].slice(0, Math.max(2, options.length));
    onChange({ ...question, type: next, options: padded });
  };
  const setOption = (at: number, value: string) =>
    onChange({ ...question, options: options.map((option, i) => (i === at ? value : option)) });
  const addOption = (after = options.length - 1) => {
    if (options.length >= LIMITS.options) return;
    const next = [...options];
    next.splice(after + 1, 0, "");
    onChange({ ...question, options: next });
    onFocusOption(after + 1);
  };
  const removeOption = (at: number) => {
    onChange({ ...question, options: options.filter((_, i) => i !== at) });
    onFocusOption(Math.max(0, at - 1));
  };

  return (
    <article className="question" style={{ "--i": index } as React.CSSProperties}>
      <header className="question-head">
        <span className="question-number">Q{index + 1}</span>
        <div className="type-switch" role="radiogroup" aria-label={`Answer type for question ${index + 1}`}>
          {(Object.keys(TYPE_LABELS) as QuestionType[]).map((kind) => (
            <button
              key={kind}
              type="button"
              role="radio"
              aria-checked={type === kind}
              className="type-option"
              title={TYPE_LABELS[kind].hint}
              onClick={() => setType(kind)}
            >
              <TypeIcon type={kind} />
              {TYPE_LABELS[kind].name}
            </button>
          ))}
        </div>
        {canRemove && (
          <button type="button" className="icon-button" onClick={onRemove} aria-label={`Remove question ${index + 1}`}>
            <CloseIcon />
          </button>
        )}
      </header>

      <label className="visually-hidden" htmlFor={`${question.id}-text`}>
        Question {index + 1}
      </label>
      <input
        id={`${question.id}-text`}
        className="question-input"
        value={instructions}
        placeholder={PLACEHOLDERS[type]}
        maxLength={400}
        onChange={(event) => onChange({ ...question, instructions: event.target.value })}
      />

      {type === "noul" ? (
        <p className="question-note">Julia-1 answers with the chance that the answer is <strong>yes</strong>.</p>
      ) : (
        <div className="options">
          <p className="options-label">
            {type === "choice" ? "Options" : "Scale, from lowest to highest"}
            {type === "choice" && (
              <span className="options-tip">Describe each in a few words, like "Billing and payments".</span>
            )}
          </p>
          <ol className={`option-list option-list--${type}`}>
            {options.map((option, at) => (
              <li key={at} className="option-row" style={{ "--level": options.length > 1 ? at / (options.length - 1) : 0 } as React.CSSProperties}>
                <span className="option-marker" aria-hidden="true">
                  {type === "score" ? at + 1 : ""}
                </span>
                <input
                  ref={(element) => {
                    optionRefs.current[at] = element;
                  }}
                  value={option}
                  maxLength={80}
                  aria-label={`${type === "choice" ? "Option" : "Level"} ${at + 1}`}
                  placeholder={type === "choice" ? `Option ${at + 1}` : at === 0 ? "Lowest" : at === options.length - 1 ? "Highest" : `Level ${at + 1}`}
                  onChange={(event) => setOption(at, event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.metaKey && !event.ctrlKey) {
                      event.preventDefault();
                      addOption(at);
                    } else if (event.key === "Backspace" && option === "" && options.length > 2) {
                      event.preventDefault();
                      removeOption(at);
                    }
                  }}
                />
                {options.length > 2 && (
                  <button type="button" className="icon-button icon-button--small" onClick={() => removeOption(at)} aria-label={`Remove ${option || `option ${at + 1}`}`}>
                    <CloseIcon />
                  </button>
                )}
              </li>
            ))}
          </ol>
          {options.length < LIMITS.options && (
            <button type="button" className="add-option" onClick={() => addOption()}>
              <PlusIcon /> Add {type === "choice" ? "option" : "level"}
            </button>
          )}
        </div>
      )}
    </article>
  );
}

export function TypeIcon({ type }: { type: QuestionType }) {
  const common = { width: 16, height: 16, viewBox: "0 0 16 16", "aria-hidden": true, fill: "none", stroke: "currentColor", strokeWidth: 1.6 } as const;
  if (type === "choice")
    return (
      <svg {...common}>
        <circle cx="3.5" cy="4" r="1.5" fill="currentColor" stroke="none" />
        <path d="M7 4h7M7 8h7M7 12h7" strokeLinecap="round" />
        <circle cx="3.5" cy="8" r="1.2" />
        <circle cx="3.5" cy="12" r="1.2" />
      </svg>
    );
  if (type === "score")
    return (
      <svg {...common}>
        <path d="M2.5 13.5v-3M6.2 13.5v-5.5M9.8 13.5V5.5M13.5 13.5v-11" strokeLinecap="round" strokeWidth="2" />
      </svg>
    );
  return (
    <svg {...common}>
      <circle cx="8" cy="8" r="5.8" />
      <path d="M8 2.2a5.8 5.8 0 0 1 0 11.6Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
      <path d="M3.5 3.5l7 7M10.5 3.5l-7 7" />
    </svg>
  );
}

export function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
      <path d="M7 2.5v9M2.5 7h9" />
    </svg>
  );
}
