import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import "./index.css";
import { installSessionReset } from "./store/sessionReset";
import { initTheme } from "./utils/theme";

// Apply the saved theme before first paint to avoid a flash on refresh.
initTheme();
// Wipe per-user state whenever the signed-in user changes (see store/sessionReset.ts).
installSessionReset();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
