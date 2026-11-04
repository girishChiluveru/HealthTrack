import { useRef } from 'react';
import ApiStatus from './ApiStatus.jsx';
import Brand from './Brand.jsx';
import Icon from './Icon.jsx';

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
              {navItems.map(({ id, label, icon }) => (
                <li key={id}>
                  <a
                    href={`#${id}`}
                    className="nav-item"
                    aria-current={id === activeView ? 'page' : undefined}
                    // Keyboard and screen reader users continue from the new view.
                    onClick={focusMain}
                  >
                    <Icon name={icon} />
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
            <button type="button" className="button button--secondary" onClick={onLogout}>
              Log out
            </button>
          </div>
        </header>

        <main ref={main} className="shell__main" tabIndex={-1}>
          {children}
        </main>

        <footer className="site-footer">
          <p>Prototype. Please do not enter real health information.</p>
          <ApiStatus />
        </footer>
      </div>
    </div>
  );
}
