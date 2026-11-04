import { useAuth } from './auth/useAuth.js';
import AccountPanel from './components/AccountPanel.jsx';
import ApiStatus from './components/ApiStatus.jsx';
import AuthPanel from './components/AuthPanel.jsx';
import SymptomEntryForm from './components/SymptomEntryForm.jsx';

export default function App() {
  const { user, isCheckingSession, notice, login, register, logout } = useAuth();

  return (
    <div className="page">
      <header className="site-header">
        <span className="brand">HealthTrack</span>
        {user && (
          <button type="button" className="button button--secondary" onClick={logout}>
            Log out
          </button>
        )}
      </header>

      <main className="hero">
        <h1>Understand how your symptoms change over time</h1>
        <p className="lead">
          Log your symptoms, follow their severity, and share your records with your doctor.
        </p>
        {isCheckingSession && <p role="status">Checking your session…</p>}
        {!isCheckingSession && user && <AccountPanel user={user} />}
        {!isCheckingSession && user?.role === 'patient' && (
          <SymptomEntryForm timezone={user.timezone} />
        )}
        {!isCheckingSession && !user && (
          <AuthPanel notice={notice} onLogin={login} onRegister={register} />
        )}
        <ApiStatus />
      </main>

      <footer className="site-footer">
        <p>Prototype. Please do not enter real health information.</p>
      </footer>
    </div>
  );
}
