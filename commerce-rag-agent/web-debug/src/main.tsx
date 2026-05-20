import React from "react";
import ReactDOM from "react-dom/client";
import { DebugConsole } from "./pages/DebugConsole";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <DebugConsole />
  </React.StrictMode>
);
