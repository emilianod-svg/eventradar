interface Props {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

// Estado "sin resultados" (sección 15.4 del plan).
export function EmptyState({ title, description, actionLabel, onAction }: Props) {
  return (
    <div className="empty-state" role="status">
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {actionLabel && onAction && (
        <button type="button" className="secondary-button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
