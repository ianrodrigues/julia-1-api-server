import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// Read public configuration from the running server, independently of the UI.
async function loadAnalytics() {
  try {
    const response = await fetch("/playground/config.json", { cache: "no-store" });
    if (!response.ok) return;
    const { umamiWebsiteId } = await response.json();
    if (typeof umamiWebsiteId !== "string" || !umamiWebsiteId.trim()) return;

    const script = document.createElement("script");
    script.defer = true;
    script.src = "https://cloud.umami.is/script.js";
    script.dataset.websiteId = umamiWebsiteId.trim();
    document.head.append(script);
  } catch {
    // Analytics is optional; configuration failures must not interrupt the playground.
  }
}

void loadAnalytics();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
