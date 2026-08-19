import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

const EVENTS = [
  {
    id: "ff705d3f-19d3-4d7b-b3b6-1e21926ded34",
    title: "46a Fiesta Nacional del Inmigrante",
    slug: "46a-fiesta-nacional-del-inmigrante-20260903",
    description: "Celebración con música, gastronomía y actividades culturales.",
    start_at: "2026-09-03T23:00:00Z",
    end_at: "2026-09-04T02:00:00Z",
    venue_name: "Parque de las Naciones",
    address: "Oberá, Misiones",
    latitude: -27.4873,
    longitude: -55.1255,
    price_text: "Entrada general",
    category: "Fiesta popular",
    image_url: null,
    status: "ACTIVE",
    quality_score: 0.982,
    source_url:
      "https://turismomisiones.com.ar/2026/08/07/se-presento-la-46a-fiesta-nacional-del-inmigrante-en-obera-un-motor-de-desarrollo-turistico-y-cultural-para-misiones/",
    source_name: "Turismo Misiones",
    source_base_url: "https://turismomisiones.com.ar/feed/",
  },
  {
    id: "15d459e7-2a55-4d2d-bf54-6101c9d0f111",
    title: "Feria gastronómica de invierno",
    slug: "feria-gastronomica-de-invierno-20261001",
    description: "Sabores regionales, cocina en vivo y propuestas para toda la familia.",
    start_at: "2026-10-01T18:00:00Z",
    end_at: "2026-10-01T23:00:00Z",
    venue_name: "Parque Paraguayo",
    address: "Posadas",
    latitude: null,
    longitude: null,
    price_text: "Desde $3000",
    category: "Gastronomía",
    image_url: null,
    status: "ACTIVE",
    quality_score: 0.741,
    source_url: "https://example.com/feria",
    source_name: "Ejemplo",
    source_base_url: "https://example.com/feed",
  },
] as const;

const CYCLES = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    status: "RUNNING",
    triggered_by: "manual",
    started_at: "2026-08-18T10:00:00Z",
    finished_at: null,
    metrics: {
      sources_processed: 1,
      sources_failed: 0,
      items_collected: 12,
      items_failed: 1,
      events_accepted: 3,
      events_merged: 1,
      events_reviewed: 2,
      events_rejected: 1,
      events_archived: 0,
    },
    error_message: null,
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    status: "FAILED",
    triggered_by: "scheduler",
    started_at: "2026-08-17T09:00:00Z",
    finished_at: "2026-08-17T09:04:30Z",
    metrics: {
      sources_processed: 0,
      sources_failed: 2,
      items_collected: 0,
      items_failed: 0,
      events_accepted: 0,
      events_merged: 0,
      events_reviewed: 0,
      events_rejected: 0,
      events_archived: 0,
    },
    error_message: "No se pudo conectar con la fuente RSS",
  },
] as const;

const CYCLE_DETAIL = {
  ...CYCLES[0],
  sources: [
    {
      id: "5e39d411-ea7b-4748-a46e-b303adc52d06",
      source_id: "52471566-1b72-405e-bb91-0643da26af89",
      status: "COMPLETED",
      items_collected: 1,
      items_accepted: 0,
      error_message: null,
      duration_ms: 2382.669589998841,
    },
    {
      id: "3dd0136e-0482-45f1-b3af-202beccd52c5",
      source_id: "b7d4fba6-ae03-4481-9776-fb7d5e35ace6",
      status: "FAILED",
      items_collected: 0,
      items_accepted: 0,
      error_message: "No se pudo descargar la página en https://ticketmisiones.com/eventos-por-ciudad?ciudad=Posadas.",
      duration_ms: 188.18774600003962,
    },
  ],
};

let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function applyFilters(url: URL) {
  const page = Number(url.searchParams.get("page") ?? "1") || 1;
  const pageSize = Number(url.searchParams.get("page_size") ?? "12") || 12;
  const query = (url.searchParams.get("query") ?? "").toLowerCase();
  const category = url.searchParams.get("category") ?? "";

  let filtered = [...EVENTS];

  if (query) {
    filtered = filtered.filter((event) => event.title.toLowerCase().includes(query));
  }

  if (category) {
    filtered = filtered.filter((event) => event.category === category);
  }

  const total = filtered.length;
  const start = (page - 1) * pageSize;
  const items = filtered.slice(start, start + pageSize);

  return { items, page, page_size: pageSize, total };
}

function mockFetch(input: RequestInfo | URL, init?: RequestInit) {
  const url = input instanceof Request ? new URL(input.url) : new URL(String(input), "http://localhost");
  const method = input instanceof Request ? input.method : init?.method ?? "GET";

  if (url.pathname.endsWith("/health")) {
    return Promise.resolve(jsonResponse({ status: "ok" }));
  }

  if (url.pathname === "/api/v1/internal/cycles") {
    if (method === "POST") {
      return Promise.resolve(jsonResponse(CYCLE_DETAIL, 201));
    }

    return Promise.resolve(jsonResponse(CYCLES));
  }

  if (url.pathname === `/api/v1/internal/cycles/${CYCLES[0].id}`) {
    return Promise.resolve(jsonResponse(CYCLE_DETAIL));
  }

  if (url.pathname.startsWith("/api/v1/events/") && url.pathname.split("/").length > 4) {
    const slug = decodeURIComponent(url.pathname.split("/").pop() ?? "");
    const event = EVENTS.find((item) => item.slug === slug);

    return Promise.resolve(event ? jsonResponse(event) : new Response("Not found", { status: 404 }));
  }

  if (url.pathname.endsWith("/api/v1/events")) {
    return Promise.resolve(jsonResponse(applyFilters(url)));
  }

  return Promise.resolve(new Response("Not found", { status: 404 }));
}

describe("App", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    window.localStorage.clear();
    fetchMock = vi.fn(mockFetch);
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("muestra el listado y enlaza al detalle estilizado", async () => {
    render(<App />);

    expect(screen.getByText(/Conectando con el backend/i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText(/Backend conectado correctamente/i)).toBeInTheDocument());

    expect(screen.getByText(/2 eventos encontrados/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Ver detalle/i })[0]).toHaveAttribute(
      "href",
      "/events/46a-fiesta-nacional-del-inmigrante-20260903"
    );
    expect(screen.getByRole("link", { name: /Turismo Misiones/i })).toHaveAttribute(
      "href",
      "https://turismomisiones.com.ar/2026/08/07/se-presento-la-46a-fiesta-nacional-del-inmigrante-en-obera-un-motor-de-desarrollo-turistico-y-cultural-para-misiones/"
    );
  });

  it("muestra la ficha estilizada del evento al entrar por URL", async () => {
    window.history.replaceState(null, "", "/events/46a-fiesta-nacional-del-inmigrante-20260903");

    render(<App />);

    await waitFor(() => expect(screen.getByRole("heading", { name: /46a Fiesta Nacional del Inmigrante/i })).toBeInTheDocument());
    expect(screen.getByText(/Entrada general/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir fuente original/i })).toHaveAttribute(
      "href",
      "https://turismomisiones.com.ar/2026/08/07/se-presento-la-46a-fiesta-nacional-del-inmigrante-en-obera-un-motor-de-desarrollo-turistico-y-cultural-para-misiones/"
    );
    expect(screen.getByTitle(/Mapa de 46a Fiesta Nacional del Inmigrante/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Ver JSON/i })).toHaveAttribute(
      "href",
      "/api/v1/events/46a-fiesta-nacional-del-inmigrante-20260903"
    );
    expect(screen.queryByText(/-27\.4873, -55\.1255/i)).not.toBeInTheDocument();
  });

  it("permite filtrar desde el listado", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByText(/Backend conectado correctamente/i)).toBeInTheDocument());

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "feria" } });

    await waitFor(() => expect(screen.getByText(/Feria gastronómica de invierno/i)).toBeInTheDocument());
    expect(screen.queryByText(/46a Fiesta Nacional del Inmigrante/i)).not.toBeInTheDocument();
  });

  it("muestra el panel de ciclos y permite disparar uno", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByText(/Backend conectado correctamente/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("tab", { name: /Ciclos/i }));
    fireEvent.change(screen.getByLabelText(/API key admin/i), { target: { value: "admin-key" } });

    await waitFor(() => expect(screen.getByText(/11111111/i)).toBeInTheDocument());
    expect(screen.getAllByText(/En ejecución/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/^Fallido$/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /11111111/i }));

    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    expect(screen.getByText(/Ciclo 11111111/i)).toBeInTheDocument();
    expect(screen.getByText(/52471566/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Cerrar detalle/i }));

    fireEvent.click(screen.getByRole("button", { name: /Fallidos primero/i }));

    await waitFor(() => {
      expect(document.querySelector(".cycles-list .cycle-row")?.textContent).toContain("22222222");
    });

    fireEvent.click(screen.getByRole("button", { name: /Correr ciclo/i }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes(`/api/v1/internal/cycles/${CYCLES[0].id}`))).toBe(true);
  });
});
