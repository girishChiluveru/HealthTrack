import { PulseStrip } from './SymptomPulse.jsx';
import ApiStatus from './ApiStatus.jsx';
import AuthPanel from './AuthPanel.jsx';
import Brand from './Brand.jsx';

// Illustration only. Null days show how days without entries appear.
const SAMPLE_DAYS = [3, 4, 4, null, 6, 7, 8, 6, null, null, 5, 4, 3, 2].map((severity, index) => ({
  key: index,
  severity,
}));

export default function AuthScreen({ notice, onLogin, onRegister }) {
  return (
    <div className="auth-screen">
      <section className="auth-screen__story">
        <Brand />
        <div>
          <h1>Understand how your symptoms change over time</h1>
          <p className="auth-screen__lead">
            Log your symptoms, follow their severity, and share your records with your doctor.
          </p>
        </div>
        <div className="auth-screen__sample" aria-hidden="true">
          <div className="pulse-row">
            <div className="pulse-row__header">
              <p className="pulse-row__name">Two weeks at a glance</p>
            </div>
            <PulseStrip days={SAMPLE_DAYS} />
          </div>
        </div>
      </section>

      <main className="auth-screen__panel">
        <AuthPanel notice={notice} onLogin={onLogin} onRegister={onRegister} />
        <div className="auth-screen__notes">
          <p>Prototype. Please do not enter real health information.</p>
          <ApiStatus />
        </div>
      </main>
    </div>
  );
}
