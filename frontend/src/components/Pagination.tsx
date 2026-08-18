interface Props {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  return (
    <nav className="pagination" aria-label="Paginación de eventos">
      <p className="pagination__summary">
        Mostrando {start} a {end} de {total}
      </p>
      <div className="pagination__actions">
        <button type="button" className="secondary-button" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
          Anterior
        </button>
        <span className="pagination__page">
          Página {page} de {totalPages}
        </span>
        <button
          type="button"
          className="secondary-button"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Siguiente
        </button>
      </div>
    </nav>
  );
}
