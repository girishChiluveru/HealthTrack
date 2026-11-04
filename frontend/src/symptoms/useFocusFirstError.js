import { useEffect } from 'react';

// Moves focus to the first invalid field each time `request` increases.
export function useFocusFirstError(formRef, request) {
  useEffect(() => {
    if (request > 0) {
      formRef.current?.querySelector('[aria-invalid="true"]')?.focus();
    }
  }, [formRef, request]);
}
