import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import Portal from './Portal';
import './styles.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode>{location.pathname === '/legacy-demo' ? <App/> : <Portal/>}</React.StrictMode>);
