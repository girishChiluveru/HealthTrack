import { useCallback, useRef, useState } from 'react';

export function useToast() {
  const [toast, setToast] = useState(null);
  const nextId = useRef(1);

  const showToast = useCallback((message) => {
    setToast({ id: nextId.current, message });
    nextId.current += 1;
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  return { toast, showToast, dismissToast };
}
