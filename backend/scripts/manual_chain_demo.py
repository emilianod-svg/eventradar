"""Demo manual de la cadena Scrapy -> Collector -> Analyzer.

Uso:
  cd backend
  python3 scripts/manual_chain_demo.py

Opcional:
  export LLM_PROVIDER=ollama
  export LLM_MODEL=minimax-m3:cloud
  export LLM_BASE_URL=http://localhost:11434
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.domain.entities import SourceDefinition
from app.sources.scrapy_adapter import ScrapyAdapter


class DemoLLMClient:
    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return {
            "is_event": True,
            "confidence": 0.91,
            "title": "Feria Artesanal de Invierno",
            "description": text,
            "category": "feria",
            "evidence": {"title": "Feria Artesanal de Invierno"},
        }


async def main() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "scrapy"
    fixture_path = fixture_path / "ticketmisiones.html"
    html = fixture_path.read_text(encoding="utf-8")

    source = SourceDefinition(
        id=uuid4(),
        name="Ticket Misiones",
        base_url="https://ticketmisiones.com",
        adapter_type="scrapy",
    )

    adapter = ScrapyAdapter()

    async def fake_download(url: str) -> str:
        return html

    adapter._download = fake_download  # type: ignore[method-assign]

    collector = CollectorAgent(scrapy_adapter=adapter)
    raw_candidates = await collector.execute(source)

    print("RAW CANDIDATES:")
    raw_payload = [candidate.model_dump(mode="json") for candidate in raw_candidates]
    print(json.dumps(raw_payload, indent=2, ensure_ascii=False))

    analyzer = AnalyzerAgent(llm_client=DemoLLMClient())
    analyzed = await analyzer.execute(raw_candidates[0])

    print("\nANALYZED EVENTS:")
    analyzed_payload = [event.model_dump(mode="json") for event in analyzed]
    print(json.dumps(analyzed_payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
