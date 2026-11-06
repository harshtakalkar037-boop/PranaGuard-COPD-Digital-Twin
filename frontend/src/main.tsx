import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import Portal from './Portal';
import '@fontsource-variable/inter';
import './styles.css';
const path = location.pathname;
const isResearchWorkspace = path === '/doctor/dashboard' || path === '/legacy-demo';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode>{isResearchWorkspace ? <App/> : <Portal/>}</React.StrictMode>);
