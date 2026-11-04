import { useState } from 'react';
import LoginForm from './LoginForm.jsx';
import RegisterForm from './RegisterForm.jsx';

export default function AuthPanel({ notice, onLogin, onRegister }) {
  const [mode, setMode] = useState('login');
  const isLogin = mode === 'login';

  return (
    <section className="card" aria-labelledby="auth-heading">
      <h2 id="auth-heading">{isLogin ? 'Log in' : 'Create your account'}</h2>
      {notice && (
        <p className="alert" role="status">
          {notice}
        </p>
      )}
      {isLogin ? <LoginForm onLogin={onLogin} /> : <RegisterForm onRegister={onRegister} />}
      <p className="auth-switch">
        {isLogin ? 'New to HealthTrack?' : 'Already have an account?'}{' '}
        <button
          type="button"
          className="link-button"
          onClick={() => setMode(isLogin ? 'register' : 'login')}
        >
          {isLogin ? 'Create an account' : 'Log in'}
        </button>
      </p>
    </section>
  );
}
