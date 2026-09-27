import type { Scenario } from "./types";

export const SCENARIOS: Scenario[] = [
  {
    id: "support",
    title: "Support inbox",
    blurb: "Route a ticket and spot an angry customer",
    state:
      "Hi, I've been charged TWICE for order #48213 and nobody has answered my last two emails. " +
      "I need the duplicate charge refunded today or I'm disputing it with my bank. " +
      "Really disappointed, I used to love this store.",
    questions: [
      {
        type: "choice",
        instructions: "Which team should handle this ticket?",
        options: ["Billing and payments", "Shipping and delivery", "Technical problems", "Account and login"],
      },
      {
        type: "score",
        instructions: "How frustrated is the customer?",
        options: ["Calm", "Annoyed", "Frustrated", "Furious"],
      },
      { type: "noul", instructions: "Is the customer asking for a refund?", options: [] },
    ],
  },
  {
    id: "review",
    title: "Product review",
    blurb: "What did they love, and what did they hate?",
    state:
      "The sound on these headphones is honestly incredible, deep bass and super clear vocals. " +
      "But after an hour they start to hurt my ears, and the battery barely lasts a day. " +
      "For $250 I expected better comfort.",
    questions: [
      {
        type: "choice",
        instructions: "What does the reviewer love most?",
        options: ["The sound", "How comfortable they are", "The battery life", "The price"],
      },
      {
        type: "choice",
        instructions: "What does the reviewer dislike most?",
        options: ["The sound", "They hurt after a while", "The battery life", "The price"],
      },
      {
        type: "score",
        instructions: "Overall, how happy is the reviewer?",
        options: ["Very unhappy", "Unhappy", "Mixed", "Happy", "Very happy"],
      },
    ],
  },

  {
    id: "delivery",
    title: "Delivery chat",
    blurb: "Understand a hungry customer in one pass",
    state:
      "Where is my order?? I ordered pizza over an hour ago and the app still says 'preparing'. " +
      "I'm starving. If it's not here in 15 minutes just cancel it.",
    questions: [
      {
        type: "choice",
        instructions: "What does the customer want?",
        options: [
          "Know where the order is",
          "Change the delivery address",
          "Complain about the food quality",
          "Add items to the order",
        ],
      },
      {
        type: "score",
        instructions: "How urgent is this?",
        options: ["Not urgent", "Somewhat urgent", "Very urgent"],
      },
      { type: "noul", instructions: "Is the customer happy?", options: [] },
    ],
  },

  {
    id: "phishing",
    title: "Scam check",
    blurb: "Is this message safe to answer?",
    state:
      "URGENT: Your bank account has been locked due to suspicious activity. To avoid permanent " +
      "closure within 24 hours, reply with your full card number, PIN and password.",
    questions: [
      { type: "noul", instructions: "Is this email a scam?", options: [] },
      {
        type: "choice",
        instructions: "What is the email trying to get from the reader?",
        options: ["Password and card details", "A reply", "Nothing, it's informational"],
      },
      {
        type: "score",
        instructions: "How much pressure does the email put on the reader to act fast?",
        options: ["None", "A little", "A lot", "Extreme"],
      },
    ],
  },

  {
    id: "sales",
    title: "Sales lead",
    blurb: "Qualify an inbound message",
    state:
      "Hey! We're a team of 40 designers evaluating tools to replace our current setup before our " +
      "contract ends in March. Could someone walk us through pricing for the business plan? " +
      "We have budget approved for this quarter.",
    questions: [
      {
        type: "choice",
        instructions: "Who should reply?",
        options: ["Sales team", "Support team", "Recruiting team"],
      },
      {
        type: "score",
        instructions: "How ready are they to buy?",
        options: ["Just browsing", "Curious", "Actively evaluating", "Ready to buy"],
      },
      { type: "noul", instructions: "Do they mention having a budget?", options: [] },
    ],
  },

];

export const BLANK: Scenario = {
  id: "blank",
  title: "Start from scratch",
  blurb: "Your own text, your own questions",
  state: "",
  questions: [{ type: "choice", instructions: "", options: ["", ""] }],
};
