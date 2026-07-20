# SVG Builder AI

Ferramenta profissional desktop (Python 3.12 + CustomTkinter) que transforma artes raster (PNG, JPG, WEBP, etc.) em **SVG modular, organizado e editável**, com camadas semânticas, vetorização offline por objeto e IA **apenas** para análise via [OpenRouter](https://openrouter.ai).

> **Status atual: Etapa 8 — Frameworks & animações**  
> Export React/Vue/Angular/Flutter/Godot/Unity + SVG animado. Pipeline profissional completo.

---

## Visão

| Capacidade | Abordagem |
|---|---|
| Importar imagem | Local (Pillow / OpenCV) |
| Super-resolution | Algoritmos locais (+ dicas opcionais de IA) |
| Remover fundo | Traditional CV + IA opcional |
| Detectar / separar objetos | OpenCV + segmentação |
| Classificar camadas | OpenRouter (análise) |
| Vetorizar | Potrace / offline **por camada** |
| Otimizar / exportar | svgwrite, shapely, exporters |

A IA **nunca** é a fonte da verdade do SVG. Vetorização funciona sem rede.

---

## Stack

- **Python 3.12**
- **UI:** CustomTkinter (etapa futura)
- **CV:** OpenCV, Pillow, NumPy, scikit-image, Potrace, shapely
- **SVG:** svgwrite, cairosvg
- **IA:** OpenRouter apenas (`OpenRouterClient` → `AIService`)
- **Config:** pydantic-settings + `.env`
- **Testes:** pytest, respx, pytest-asyncio

---

## Arquitetura (Clean Architecture)

```
src/
├── config/          # Settings tipados (.env)
├── core/            # DI, eventos (Observer), commands, bootstrap, interfaces
├── models/          # Layer, ProjectDocument, Bounds
├── services/
│   └── ai/          # OpenRouterClient + AIService
├── processors/      # Strategy + PluginRegistry (plugins sem tocar o core)
├── ui/              # CustomTkinter (shell na próxima etapa)
├── utils/           # Logging
└── main.py          # Entrypoint
exports/  assets/  cache/  logs/
tests/    docs/
```

Padrões já preparados:

- **Strategy** — processadores
- **Factory** — `PluginRegistry`
- **Observer** — `EventBus`
- **Command** — `CommandHistory` (undo/redo)
- **Repository** — interface `LayerRepository`
- **DI** — `Container` + composition root `bootstrap.py`

Veja o diagrama detalhado em [`docs/architecture/overview.md`](docs/architecture/overview.md).

---

## Instalação

### Pré-requisitos

- Python **3.12+**
- (Windows) Visual C++ Build Tools podem ser necessários para alguns wheels (cairosvg/potrace)

### Setup

```powershell
cd "C:\Users\WINDOWS 11\Projects\svg-builder-ai"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
# ou: pip install -e ".[dev]"
```

### Configuração OpenRouter

```powershell
Copy-Item .env.example .env
# Edite .env e preencha OPENROUTER_API_KEY
```

Variáveis principais:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=deepseek/deepseek-chat
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Qualquer modelo do OpenRouter funciona (DeepSeek, Qwen, Claude, GPT, Gemini, …) trocando `OPENROUTER_MODEL`.

---

## Executar

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.main
```

Abre a interface desktop.

1. **Importar imagem** — carrega PNG/JPG/WEBP/…
2. **Melhorar qualidade** — upscale 2× offline (bilateral + Lanczos + unsharp)
3. **Remover fundo** — flood-fill das bordas (padrão); GrabCut disponível via API
4. **Detectar objetos** — contornos OpenCV + overlay
5. **Separar camadas** — um `Layer` por objeto (`building_01`, …) + painel na UI
6. **Vetorizar** — Potrace por camada → SVG modular com `<g id="...">`
7. **Otimizar SVG** — simplifica paths, remove vazios/duplicatas
8. **Exportar** — diálogo de formato (SVG / SVG otimizado / JSON / PNG / WEBP)
9. **Canvas** — zoom/pan/grid, editar camadas (cor, opacidade, ordem, duplicar, excluir)
10. **Frameworks** — React (`<Building01/>`), Vue, Angular, Flutter, Godot, Unity + SVG animado

Pipeline comercial-ready nas 8 etapas entregues.

---

## Testes

```powershell
pytest -q
```

---

## Camada de IA

```text
UI / Processors  →  AIService  →  OpenRouterClient  →  OpenRouter API
                         ↑
              (análise: classificar, nomear, agrupar, descrever)
```

- Nenhuma SDK direta da OpenAI / Anthropic / Google.
- `AIService.classify_objects`, `suggest_structure`, `describe_image_context`.
- Se `OPENROUTER_API_KEY` estiver vazio, `AIService` sobe com `enabled=False` e o pipeline offline segue normalmente.

Documentação das classes: [`docs/api/ai-layer.md`](docs/api/ai-layer.md).

---

## Roadmap

| Etapa | Conteúdo | Status |
|------|----------|--------|
| **1** | Estrutura, config, logging, DI, OpenRouter/AIService, plugins base | ✅ |
| **2** | UI CustomTkinter (shell, painel, previews, import) | ✅ |
| **3** | Pipeline: load, upscale, background removal | ✅ |
| **4** | Detecção de objetos + separação de camadas | ✅ |
| **5** | Vetorização por camada (Potrace → `<g id>`) | ✅ |
| **6** | Otimização SVG + exports (SVG/JSON/PNG/WEBP) | ✅ |
| **7** | Preview interativo (zoom/pan/layers CRUD) | ✅ |
| **8** | Export frameworks (React/Vue/…) + animações | ✅ |

---

## Licença

MIT (planejada para o produto open-core; a evoluir conforme comercialização).
