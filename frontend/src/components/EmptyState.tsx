interface Props {
  title: string;
  description?: string;
}

// Estado "sin resultados" (sección 15.4 del plan).
export function EmptyState({ title, description }: Props) {
  return (
    <div className="empty-state" role="status">
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}
