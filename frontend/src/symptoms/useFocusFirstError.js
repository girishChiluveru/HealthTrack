import { useEffect } from 'react';

// Moves focus to the first invalid field each time `request` increases.
export function useFocusFirstError(formRef, request) {
  useEffect(() => {
    if (request > 0) {
      const invalid = formRef.current?.querySelector('[aria-invalid="true"]');
      // A group of radio buttons is marked as a whole, but only its inputs can take focus.
      (invalid?.matches('fieldset') ? invalid.querySelector('input') : invalid)?.focus();
    }
  }, [formRef, request]);
}
