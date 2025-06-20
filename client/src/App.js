import React, { useState } from 'react';

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setResult("Loading...");

    // Determine the backend URL based on the environment
    const backendUrl = process.env.REACT_APP_BACKEND_URL || ''; // <-- This is the important part

    try {
      // Prepend the backendUrl for production deployments
      const response = await fetch(`${backendUrl}/download`, { // <-- And this usage
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
