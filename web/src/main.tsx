import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./index.css";

function restoreGithubPagesPathRedirect() {
  const query = new URLSearchParams(window.location.search);
  const redirectedPath = query.get("p");
  if (!redirectedPath) {
    return;
  }

  const restored = redirectedPath.startsWith("/") ? redirectedPath : `/${redirectedPath}`;
  const next = `${restored}${query.get("q") ? `?${query.get("q")}` : ""}${window.location.hash}`;
  window.history.replaceState(null, "", next);
}

restoreGithubPagesPathRedirect();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
