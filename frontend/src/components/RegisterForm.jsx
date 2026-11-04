import { useState } from 'react';
import { useAuthForm } from '../auth/useAuthForm.js';
import FormField from './FormField.jsx';

const ROLES = [
  { value: 'patient', label: 'Patient' },
  { value: 'doctor', label: 'Doctor' },
];

export default function RegisterForm({ onRegister }) {
  const [values, setValues] = useState({ name: '', email: '', password: '', role: 'patient' });
  const { isSubmitting, errors, submit } = useAuthForm(onRegister);

  function handleChange(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    submit(values);
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {errors.form && (
        <p className="alert alert--error" role="alert">
          {errors.form}
        </p>
      )}
      <FormField
        label="Name"
        name="name"
        autoComplete="name"
        required
        maxLength={100}
        value={values.name}
        onChange={handleChange}
        error={errors.fields.name}
      />
      <FormField
        label="Email"
        type="email"
        name="email"
        autoComplete="email"
        required
        value={values.email}
        onChange={handleChange}
        error={errors.fields.email}
      />
      <FormField
        label="Password"
        type="password"
        name="password"
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={128}
        hint="At least 8 characters."
        value={values.password}
        onChange={handleChange}
        error={errors.fields.password}
      />
      <fieldset className="role-field">
        <legend>I am a</legend>
        {ROLES.map(({ value, label }) => (
          <label key={value} className="role-field__option">
            <input
              type="radio"
              name="role"
              value={value}
              checked={values.role === value}
              onChange={handleChange}
            />
            {label}
          </label>
        ))}
        {errors.fields.role && <p className="field__error">{errors.fields.role}</p>}
      </fieldset>
      {errors.fields.timezone && <p className="field__error">{errors.fields.timezone}</p>}
      <button type="submit" className="button" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </button>
    </form>
  );
}
