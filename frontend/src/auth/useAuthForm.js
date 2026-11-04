import { useState } from 'react';

const INITIAL_ERRORS = { form: '', fields: {} };

export function useAuthForm(submitAction) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState(INITIAL_ERRORS);

  async function submit(values) {
    setIsSubmitting(true);
    setErrors(INITIAL_ERRORS);
    try {
      await submitAction(values);
    } catch (error) {
      const fields = error.fieldErrors ?? {};
      const hasFieldErrors = Object.keys(fields).length > 0;
      setErrors({ form: hasFieldErrors ? '' : error.message, fields });
      setIsSubmitting(false);
    }
  }

  return { isSubmitting, errors, submit };
}
