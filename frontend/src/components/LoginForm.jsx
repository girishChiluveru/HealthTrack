import { useState } from 'react';
import { useAuthForm } from '../auth/useAuthForm.js';
import FormField from './FormField.jsx';

export default function LoginForm({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { isSubmitting, errors, submit } = useAuthForm(onLogin);

  function handleSubmit(event) {
    event.preventDefault();
    submit({ email, password });
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {errors.form && (
        <p className="alert alert--error" role="alert">
          {errors.form}
        </p>
      )}
      <FormField
        label="Email"
        type="email"
        name="email"
        autoComplete="email"
        spellCheck={false}
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={errors.fields.email}
      />
      <FormField
        label="Password"
        type="password"
        name="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.fields.password}
      />
      <button type="submit" className="button" disabled={isSubmitting}>
        {isSubmitting ? 'Logging in…' : 'Log in'}
      </button>
    </form>
  );
}
