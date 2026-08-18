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

function mockFetch(input: RequestInfo | URL) {
  const url = new URL(String(input), "http://localhost");

  if (url.pathname.endsWith("/health")) {
    return Promise.resolve(jsonResponse({ status: "ok" }));
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
    vi.stubGlobal("fetch", vi.fn(mockFetch));
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
});
