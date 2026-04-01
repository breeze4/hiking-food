import { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Hiking Food Planner</h1>
      {error && <p style={{ color: 'red' }}>Backend error: {error}</p>}
      {health && <p>Backend status: {health.status}</p>}
      {!health && !error && <p>Connecting to backend...</p>}
    </div>
  )
}

export default App
