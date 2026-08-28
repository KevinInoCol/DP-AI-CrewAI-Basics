# CrewAI — Creando Sistemas Multi-Agente

**Programa AI Engineer · Módulo 5 · Sesión 1**

Material de clase para construir sistemas multi-agente con [CrewAI](https://crewai.com):
desde un crew mínimo en un notebook hasta dos proyectos completos con herramientas
propias, herramientas externas y observabilidad.

---

## Contenido

| # | Material | Qué se ve |
|---|---|---|
| 1 | `01_blog_post_crew.ipynb` | El crew más simple posible, todo en un notebook: 4 agentes y 5 tareas en proceso secuencial. Punto de partida de la sesión. |
| 2 | `02_Crear_Proyecto_de_CrewAI_APUNTES.md` | Apuntes del comando `crewai create crew` para pasar del notebook a un proyecto estructurado. |
| 3 | `proyecto_agentes_de_pipeline_ml/` | Proyecto A — 9 agentes que construyen un pipeline de Machine Learning completo, con **herramientas propias**. |
| 4 | `proyecto_b_agentes_con_tools_y_observabilidad/` | Proyecto B — 4 agentes que redactan un post de blog, con **herramientas externas** y **observabilidad**. |

---

## Proyecto A · Agentes de pipeline de ML

Un crew secuencial de 9 agentes que recorre el ciclo completo de un proyecto de ML
sobre un dataset tabular y va escribiendo los notebooks del pipeline:

```
data_analyst → feature_engineer → pipeline_builder → feature_selector →
model_selector → model_trainer → scorer → final_pipeline_builder → code_reviewer
```

- **Dataset de ejemplo:** `data/train.csv` (precios de vivienda, objetivo `SalePrice`).
- **Salida:** los notebooks generados en `proyecto_pipeline_machine_learning_muestra/`.
- **Herramientas propias:** `CSVProfilerTool`, `NotebookWriterTool`, `FileReaderTool`.

## Proyecto B · Agentes con tools y observabilidad

Un crew de 4 agentes que investiga, planifica, escribe y revisa un post de blog:

```
investigador_de_contenido → planificador_de_contenido → escritor_del_blog → revisor_de_contenido
```

- **Herramientas externas:** `SerperDevTool` (búsqueda), `ScrapeWebsiteTool` (scraping), `FileWriterTool`.
- **Observabilidad:** [AgentOps](https://agentops.ai) para trazar cada ejecución del crew.
- **Salida:** los artículos en `Results/`.

---

## Cómo ejecutar

Cada proyecto trae su propio **`Comandos.md`** con los 4 pasos. El flujo es el mismo
en los dos:

```bash
cd <carpeta_del_proyecto>
uv venv --prompt <nombre_del_entorno>   # 1. crear el entorno
source .venv/bin/activate               # 2. activarlo
uv sync                                 # 3. instalar dependencias
crewai run                              # 4. ejecutar el crew
```

Los proyectos usan [uv](https://docs.astral.sh/uv/): las dependencias viven en el
`pyproject.toml` de cada uno y quedan fijadas en su `uv.lock`. Para el notebook del
punto 1 se usa el `requirements.txt` de la raíz.

### API keys

Cada proyecto necesita su propio `.env` (nunca se sube al repositorio):

| Proyecto | Claves |
|---|---|
| A · pipeline de ML | `OPENAI_API_KEY`, `MODEL` |
| B · tools y observabilidad | `OPENAI_API_KEY`, `MODEL`, `AGENTOPS_API_KEY`, `SERPER_API_KEY` |

---

## Estructura

```
.
├── .claude/rules/          # Reglas que Claude Code carga en cada sesión
├── 01_blog_post_crew.ipynb
├── 02_Crear_Proyecto_de_CrewAI_APUNTES.md
├── proyecto_agentes_de_pipeline_ml/
└── proyecto_b_agentes_con_tools_y_observabilidad/
```

Ambos proyectos siguen el layout canónico de `crewai create`: los agentes y las
tareas se declaran en `src/<proyecto>/config/*.yaml`, el crew se ensambla con
decoradores en `crew.py`, y `main.py` es solo el runner.

## Trabajar con Claude Code

`.claude/rules/crewai-project-structure.md` fija la estructura y la sintaxis que
debe respetar cualquier cambio en un proyecto CrewAI de este repositorio. Claude Code
la carga automáticamente al iniciar cada sesión, sin que haya que pedírselo.
