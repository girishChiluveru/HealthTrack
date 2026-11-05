import { LogOut } from 'lucide-react';
import { useRef } from 'react';
import Brand from './Brand.jsx';
import ThemeToggle from './ThemeToggle.jsx';

const ROLE_LABELS = { patient: 'Patient', doctor: 'Doctor' };

export default function AppShell({ user, navItems, activeView, onLogout, children }) {
  const main = useRef(null);
  const subtitle = navItems.find(({ id }) => id === activeView)?.subtitle;

  function focusMain() {
    main.current?.focus();
  }

  return (
    <div className="shell">
      <button type="button" className="skip-link" onClick={focusMain}>
        Skip to content
      </button>
      <aside className="sidebar">
        <div className="sidebar__inner">
          <Brand />
          <nav className="sidebar__nav" aria-label="Main">
            <ul>
              {navItems.map(({ id, label, icon: Glyph }) => (
                <li key={id}>
                  <a
                    href={`#${id}`}
                    className="nav-item"
                    aria-current={id === activeView ? 'page' : undefined}
                    // Keyboard and screen reader users continue from the new view.
                    onClick={focusMain}
                  >
                    <Glyph size={20} aria-hidden="true" />
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </aside>

      <div className="shell__content">
        <header className="topbar">
          <div>
            <h1>Welcome, {user.name}</h1>
            <p className="topbar__subtitle">{subtitle}</p>
          </div>
          <div className="topbar__actions">
            <span className="role-chip">{ROLE_LABELS[user.role]}</span>
            <ThemeToggle />
            <button type="button" className="button button--secondary" onClick={onLogout}>
              <LogOut size={16} aria-hidden="true" />
              Log out
            </button>
          </div>
        </header>

        <main ref={main} className="shell__main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
