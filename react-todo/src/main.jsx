import { createRoot } from 'react-dom/client';
import './shared/todo.css';
import App from './App.jsx';

// No <StrictMode>: it double-invokes renders in development and would skew
// manual measurements. Benchmarks run against the production build anyway.
createRoot(document.getElementById('app')).render(<App />);
