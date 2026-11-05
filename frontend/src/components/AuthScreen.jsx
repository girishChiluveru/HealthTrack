import { ChartLine, ClipboardPen, ShieldCheck } from 'lucide-react';
import { useRef, useState } from 'react';
import { PulseStrip } from './SymptomPulse.jsx';
import AuthPanel from './AuthPanel.jsx';
import Brand from './Brand.jsx';
import ThemeToggle from './ThemeToggle.jsx';

// Illustration only. Null days show how days without entries appear.
const SAMPLE_SEVERITIES = [3, 4, 4, null, 6, 7, 8, 6, null, null, 5, 4, 3, 2];
const SAMPLE_DAYS = SAMPLE_SEVERITIES.map((severity, index) => ({ key: index, severity }));

const BENEFITS = [
  {
    icon: ClipboardPen,
    title: 'Log several symptoms at once',
    text: 'Record each one with a date, a 1–10 severity, and optional notes.',
  },
  {
    icon: ChartLine,
    title: 'See how they change',
    text: 'Compare symptoms on one chart. Days you did not log stay as gaps.',
  },
  {
    icon: ShieldCheck,
    title: 'Share on your terms',
    text: 'Give a doctor read-only access, and end it whenever you choose.',
  },
];

const CHART_WIDTH = 520;
const CHART_HEIGHT = 84;
const CHART_INSET = 6;

function samplePoint(severity, index) {
  const stepX = (CHART_WIDTH - CHART_INSET * 2) / (SAMPLE_SEVERITIES.length - 1);
  const usableHeight = CHART_HEIGHT - CHART_INSET * 2;
  const y = CHART_HEIGHT - CHART_INSET - ((severity - 1) / 9) * usableHeight;
  return { x: CHART_INSET + index * stepX, y };
}

function sampleSegments() {
  const segments = [[]];
  SAMPLE_SEVERITIES.forEach((severity, index) => {
    if (severity === null) {
      segments.push([]);
    } else {
      segments.at(-1).push(samplePoint(severity, index));
    }
  });
  return segments.filter((segment) => segment.length > 0);
}

function SampleTrend() {
  const segments = sampleSegments();
  return (
    <svg className="sample-trend" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}>
      {segments.map((points) => (
        <polyline
          key={points[0].x}
          points={points.map(({ x, y }) => `${x},${y}`).join(' ')}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
      {segments.flat().map(({ x, y }) => (
        <circle key={x} cx={x} cy={y} r="3" fill="var(--color-primary)" />
      ))}
    </svg>
  );
}

export default function AuthScreen({ notice, onLogin, onRegister }) {
  const [mode, setMode] = useState('login');
  const panel = useRef(null);

  function openForm(nextMode) {
    setMode(nextMode);
    // After this render, because the requested form may not be on the page yet.
    requestAnimationFrame(() => panel.current?.querySelector('input:not([type="radio"])')?.focus());
  }

  return (
    <div className="auth-screen">
      <div className="auth-screen__theme">
        <ThemeToggle />
      </div>
      <section className="auth-screen__story">
        <Brand />
        <div>
          <h1>Understand how your symptoms change over time</h1>
          <p className="auth-screen__lead">
            Log your symptoms, follow their severity, and share your records with your doctor.
          </p>
        </div>
        <div className="action-row">
          <button type="button" className="button" onClick={() => openForm('register')}>
            Create an account
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => openForm('login')}
          >
            Log in
          </button>
        </div>
      </section>

      <main ref={panel} className="auth-screen__panel">
        <AuthPanel
          mode={mode}
          notice={notice}
          onModeChange={setMode}
          onLogin={onLogin}
          onRegister={onRegister}
        />
      </main>

      <section className="auth-screen__details" aria-label="What HealthTrack does">
        <div className="auth-screen__sample" aria-hidden="true">
          <p className="auth-screen__sample-title">Sample data: two weeks of one symptom</p>
          <SampleTrend />
          <PulseStrip days={SAMPLE_DAYS} />
        </div>
        <ul className="benefits">
          {BENEFITS.map(({ icon: Glyph, title, text }) => (
            <li key={title} className="benefit">
              <span className="benefit__icon">
                <Glyph size={20} aria-hidden="true" />
              </span>
              <div>
                <h2>{title}</h2>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
