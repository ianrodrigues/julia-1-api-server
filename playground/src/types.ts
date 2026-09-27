export type QuestionType = "choice" | "score" | "noul";

export interface Question {
  id: string;
  type: QuestionType;
  instructions: string;
  /** Choice options, or score levels from lowest to highest. Unused by yes/no questions. */
  options: string[];
}

export interface Scenario {
  id: string;
  title: string;
  blurb: string;
  state: string;
  questions: Omit<Question, "id">[];
}

export interface ChoiceAnswer {
  type: "choice";
  choice: string;
  probabilities: Record<string, number>;
  confidence: number;
}

export interface ScoreAnswer {
  type: "score";
  score: number;
  legend: Record<string, string>;
  probabilities: Record<string, number>;
  confidence: number;
}

export interface NoulAnswer {
  type: "noul";
  noul: number;
}

export type Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer;

export interface SystemOneResponse {
  model: string;
  answers: Record<string, Answer>;
  usage: { input_tokens: number; output_tokens: number };
}

export const TYPE_LABELS: Record<QuestionType, { name: string; hint: string }> = {
  choice: { name: "Pick one", hint: "Choose the best option from a list" },
  score: { name: "Rate it", hint: "Place it on a scale, lowest to highest" },
  noul: { name: "Yes or no", hint: "How likely the answer is yes" },
};

export const LIMITS = { questions: 8, options: 20, text: 20000 };
