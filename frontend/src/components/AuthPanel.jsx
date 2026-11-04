import LoginForm from './LoginForm.jsx';
import RegisterForm from './RegisterForm.jsx';
import SegmentedControl from './SegmentedControl.jsx';

const MODE_OPTIONS = [
  { value: 'login', label: 'Log in' },
  { value: 'register', label: 'Create account' },
];

export default function AuthPanel({ mode, notice, onModeChange, onLogin, onRegister }) {
  const isLogin = mode === 'login';

  return (
    <section className="card" aria-labelledby="auth-heading">
      <SegmentedControl
        label="Log in or create an account"
        options={MODE_OPTIONS}
        value={mode}
        onChange={onModeChange}
      />
      <h2 id="auth-heading" className="auth-heading">
        {isLogin ? 'Welcome back' : 'Create your account'}
      </h2>
      {notice && (
        <p className="alert" role="status">
          {notice}
        </p>
      )}
      {isLogin ? <LoginForm onLogin={onLogin} /> : <RegisterForm onRegister={onRegister} />}
    </section>
  );
}
