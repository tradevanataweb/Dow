// client/src/App.js
import React, { useState } from 'react';

// Use environment variable or fallback to local
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setResult("Loading...");

    try {
      const response = await fetch(`${API_URL}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setResult("Error: " + err.message);
    }
  };

  return (
    <div className="app">
      <h1>Downloader API</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Enter URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <button type="submit">Download</button>
      </form>
      <pre>{result}</pre>
    </div>
  );
}

export default App;
