import { useId, useLayoutEffect, useRef } from 'react';

export default function ConfirmDialog({
  title,
  children,
  confirmLabel,
  busyLabel,
  cancelLabel,
  isBusy,
  error,
  onConfirm,
  onCancel,
}) {
  const id = useId();
  const dialog = useRef(null);
  const cancelButton = useRef(null);

  // A layout effect, because focus can only return while the dialog is still in the page.
  useLayoutEffect(() => {
    const element = dialog.current;
    element.showModal();
    cancelButton.current.focus();
    return () => element.close();
  }, []);

  function cancelUnlessBusy() {
    if (!isBusy) {
      onCancel();
    }
  }

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-body`}
      onCancel={(event) => {
        event.preventDefault();
        cancelUnlessBusy();
      }}
      onClick={(event) => {
        // Only the backdrop reports the dialog itself as the target.
        if (event.target === dialog.current) {
          cancelUnlessBusy();
        }
      }}
    >
      <div className="dialog__body">
        <h2 id={`${id}-title`}>{title}</h2>
        <div id={`${id}-body`}>{children}</div>
        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog__actions">
          <button
            ref={cancelButton}
            type="button"
            className="button button--secondary"
            disabled={isBusy}
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className="button button--danger"
            disabled={isBusy}
            onClick={onConfirm}
          >
            {isBusy ? busyLabel : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
