/*
This file is the starting point of the react frontend.
It puts the App component into the page, inside the element with id "root".
*/
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// show the App on the page
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
