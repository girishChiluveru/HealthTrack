// A button with no visible text. `label` is its accessible name and its tooltip.
export default function IconButton({
  label,
  icon: Glyph,
  tooltip = true,
  danger = false,
  ...buttonProps
}) {
  return (
    <button
      type="button"
      className={danger ? 'icon-button icon-button--danger' : 'icon-button'}
      aria-label={label}
      data-tooltip={tooltip ? label : undefined}
      {...buttonProps}
    >
      <Glyph size={18} aria-hidden="true" />
    </button>
  );
}
