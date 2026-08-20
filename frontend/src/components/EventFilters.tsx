interface EventFilterValues {
  query: string;
  category: string;
  dateFrom: string;
  dateTo: string;
  pageSize: number;
}

interface Props extends EventFilterValues {
  categories: string[];
  onChange: (patch: Partial<EventFilterValues>) => void;
  onReset: () => void;
}

export function EventFilters({
  query,
  category,
  dateFrom,
  dateTo,
  pageSize,
  categories,
  onChange,
  onReset,
}: Props) {
  return (
    <section className="filters-panel" aria-label="Filtros de eventos">
      <div className="filters-panel__grid">
        <label className="field">
          <span>Buscar</span>
          <input
            type="search"
            value={query}
            onChange={(event) => onChange({ query: event.target.value })}
            placeholder="Título o texto"
          />
        </label>

        <label className="field">
          <span>Categoría</span>
          <input
            list="event-categories"
            value={category}
            onChange={(event) => onChange({ category: event.target.value })}
            placeholder="Ej. Música / Recital"
          />
          <datalist id="event-categories">
            {categories.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </label>

        <label className="field">
          <span>Desde</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => onChange({ dateFrom: event.target.value })}
          />
        </label>

        <label className="field">
          <span>Hasta</span>
          <input
            type="date"
            value={dateTo}
            onChange={(event) => onChange({ dateTo: event.target.value })}
          />
        </label>

        <label className="field field--compact">
          <span>Por página</span>
          <select
            value={pageSize}
            onChange={(event) => onChange({ pageSize: Number(event.target.value) })}
          >
            <option value={12}>12</option>
            <option value={24}>24</option>
            <option value={48}>48</option>
          </select>
        </label>

        <div className="filters-panel__actions">
          <button type="button" className="secondary-button" onClick={onReset}>
            Limpiar
          </button>
        </div>
      </div>
    </section>
  );
}
