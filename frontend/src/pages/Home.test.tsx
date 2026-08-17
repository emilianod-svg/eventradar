import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Home } from "./Home";

describe("Home", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/health")) {
        return Promise.resolve(
          new Response(JSON.stringify({ status: "ok" }), { status: 200 })
        );
      }

      if (url.endsWith("/api/v1/events")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  id: "ff705d3f-19d3-4d7b-b3b6-1e21926ded34",
                  title: "Recital de Litoral Groove en Plaza 9 de Julio",
                  slug: "recital-de-litoral-groove-en-plaza-9-de-julio-20260920",
                  description:
                    "Se presentará la banda Litoral Groove en un show único, no recurrente, al aire libre.",
                  start_at: "2026-09-20T23:00:00Z",
                  end_at: "2026-09-21T02:00:00Z",
                  venue_name: "Plaza 9 de Julio",
                  address: "Plaza 9 de Julio, Posadas",
                  latitude: -27.369,
                  longitude: -55.8968,
                  price_text: "Entrada gratuita",
                  category: "Música / Recital",
                  image_url: null,
                  status: "ACTIVE",
                },
              ],
              page: 1,
              page_size: 20,
              total: 1,
            }),
            { status: 200 }
          )
        );
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("muestra el estado de carga y luego confirma la conexión con el backend", async () => {
    render(<Home />);

    expect(screen.getByText(/Conectando con el backend/i)).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByText(/Backend conectado correctamente/i)).toBeInTheDocument()
    );

    expect(
      screen.getByText(/Recital de Litoral Groove en Plaza 9 de Julio/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Categoría: Música \/ Recital/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Entrada gratuita/i)).toBeInTheDocument();
    expect(screen.getByText(/Plaza 9 de Julio, Posadas/i)).toBeInTheDocument();
    expect(screen.getByText(/-27\.3690, -55\.8968/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Detalle/i }));

    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    expect(screen.getByText(/Detalle del evento/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir mapa/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir detalle/i })).toHaveAttribute(
      "href",
      "/api/v1/events/recital-de-litoral-groove-en-plaza-9-de-julio-20260920"
    );
  });
});
