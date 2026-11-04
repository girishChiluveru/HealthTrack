import ApiStatus from './components/ApiStatus.jsx';

export default function App() {
  return (
    <div className="page">
      <header className="site-header">
        <span className="brand">HealthTrack</span>
      </header>

      <main className="hero">
        <h1>Understand how your symptoms change over time</h1>
        <p className="lead">
          Log your symptoms, follow their severity, and share your records with your doctor.
        </p>
        <ApiStatus />
      </main>

      <footer className="site-footer">
        <p>Prototype. Please do not enter real health information.</p>
      </footer>
    </div>
  );
}
