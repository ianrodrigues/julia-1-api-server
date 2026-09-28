import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// Inlined at build time from UMAMI_WEBSITE_ID. When it is unset, the bundle keeps the
// lookup, and browsers have no `process`, so builds without it load no analytics.
const umamiWebsiteId = typeof process === "undefined" ? undefined : process.env.UMAMI_WEBSITE_ID;
if (umamiWebsiteId) {
  const script = document.createElement("script");
  script.defer = true;
  script.src = "https://cloud.umami.is/script.js";
  script.dataset.websiteId = umamiWebsiteId;
  document.head.append(script);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
