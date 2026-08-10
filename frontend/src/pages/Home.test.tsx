import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Home } from "./Home";

describe("Home", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ status: "ok" }), { status: 200 })
        )
      )
    );
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

    expect(screen.getByText(/Todavía no hay eventos cargados/i)).toBeInTheDocument();
  });
});
