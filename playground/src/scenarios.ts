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
    id: "catalog",
    title: "Product catalog",
    blurb: "File a new product under the right category",
    state:
      "Anker 737 Power Bank, 24,000mAh portable charger with 140W output, USB-C, smart digital " +
      "display. Charges laptops, iPhone 15 and Galaxy phones.",
    questions: [
      {
        type: "choice",
        instructions: "Which store category does this product belong in?",
        options: [
          "Electronics and gadgets",
          "Kitchen and cookware",
          "Beauty, skin and hair care",
          "Clothing and shoes",
          "Toys and games for kids",
          "Pet food and supplies",
        ],
      },
      {
        type: "choice",
        instructions: "Which subcategory fits best?",
        options: ["Chargers and power banks", "Phone cases", "Headphones and speakers", "Cables and adapters"],
      },
      {
        type: "score",
        instructions: "What price range is this product in?",
        options: ["Budget", "Mid-range", "Premium"],
      },
    ],
  },
  {
    id: "expense",
    title: "Expense report",
    blurb: "Sort a receipt into the right bucket",
    state: "Team lunch with a client at an Italian restaurant, 4 people, $186.40",
    questions: [
      {
        type: "choice",
        instructions: "Which expense category does this belong to?",
        options: ["Travel", "Meals and entertainment", "Software and subscriptions", "Office supplies", "Equipment"],
      },
      {
        type: "choice",
        instructions: "What kind of meal was it?",
        options: ["Breakfast", "Lunch", "Dinner", "Coffee or snacks"],
      },
      {
        type: "score",
        instructions: "How large is this expense?",
        options: ["Small", "Medium", "Large"],
      },
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



];

export const BLANK: Scenario = {
  id: "blank",
  title: "Start from scratch",
  blurb: "Your own text, your own questions",
  state: "",
  questions: [{ type: "choice", instructions: "", options: ["", ""] }],
};
