# Regla: Estructura y Sintaxis Canónica de Proyectos CrewAI

> **Aplica a:** todos los proyectos CrewAI dentro de esta sesión/repositorio.
> **Proyecto de referencia (fuente de verdad):** `proyecto_a_agente_basico`
> Esta es la estructura original generada por `crewai create` y **debe respetarse en cada cambio o implementación** que se haga en los proyectos de CrewAI.

---

## 1. Principio general

Cualquier cambio, refactor, agente, tarea o herramienta nuevo que se implemente en **cualquier** proyecto CrewAI de este repo **debe seguir la estructura de carpetas y la sintaxis de `proyecto_a_agente_basico`**. No inventar layouts alternativos, no mover archivos fuera de su ubicación canónica, no cambiar el estilo de los decoradores.

Si hay conflicto entre estas reglas y la documentación oficial vigente de CrewAI (ver `AGENTS.md` del proyecto), **gana la documentación oficial** — y luego se actualiza esta regla.

---

## 2. Estructura de carpetas obligatoria

```
<nombre_proyecto>/
├── .env                        # Variables de entorno / API keys (NUNCA se commitea)
├── .gitignore                  # Incluye .env, __pycache__/, .DS_Store
├── AGENTS.md                   # Referencia CrewAI para asistentes de IA (auto-generado)
├── README.md
├── pyproject.toml              # Config del proyecto + scripts + dependencias
├── knowledge/                  # Fuentes de conocimiento (opcional)
│   └── user_preference.txt
├── tests/
└── src/
    └── <nombre_proyecto>/      # Mismo nombre del proyecto (snake_case)
        ├── __init__.py
        ├── main.py             # Punto de entrada: run/train/replay/test
        ├── crew.py             # Definición del Crew con decoradores
        ├── config/
        │   ├── agents.yaml     # Definición declarativa de agentes
        │   └── tasks.yaml      # Definición declarativa de tareas
        └── tools/
            ├── __init__.py
            └── custom_tool.py  # Herramientas personalizadas
```

Reglas de nombres:
- El nombre del paquete en `src/<nombre_proyecto>/` va en **snake_case** y coincide con el nombre del proyecto.
- La clase del crew en `crew.py` va en **PascalCase** (ej. `proyecto_a_agente_basico` → `ProyectoAAgenteBasico`).

---

## 3. Sintaxis de `crew.py`

- Usar la clase decorada con `@CrewBase`.
- Declarar los type hints de clase: `agents: list[BaseAgent]` y `tasks: list[Task]`.
- Cada agente es un método decorado con `@agent` que retorna `Agent(config=self.agents_config['<clave>'], ...)`.
- Cada tarea es un método decorado con `@task` que retorna `Task(config=self.tasks_config['<clave>'], ...)`.
- El crew es un método decorado con `@crew` que retorna `Crew(agents=self.agents, tasks=self.tasks, process=..., verbose=True)`.
- **NO** listar manualmente agentes/tareas dentro de `Crew(...)`: se autogeneran por los decoradores `@agent` y `@task`.
- Las claves usadas (`self.agents_config['x']`, `self.tasks_config['x']`) **deben existir** en `config/agents.yaml` y `config/tasks.yaml`.

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

@CrewBase
class NombreDelCrew():
    """NombreDelCrew crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],  # type: ignore[index]
            verbose=True
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # Autogenerado por @agent
            tasks=self.tasks,     # Autogenerado por @task
            process=Process.sequential,
            verbose=True,
        )
```

---

## 4. Sintaxis de `config/agents.yaml`

Cada agente se define declarativamente con `role`, `goal` y `backstory`, usando el estilo de bloque `>` y placeholders `{variable}` interpolables desde los `inputs`.

```yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering the latest
    developments in {topic}.
```

- La **clave** del agente debe coincidir con la usada en `self.agents_config['<clave>']` de `crew.py`.

---

## 5. Sintaxis de `config/tasks.yaml`

Cada tarea se define con `description`, `expected_output` y `agent` (que referencia la clave de un agente en `agents.yaml`).

```yaml
research_task:
  description: >
    Conduct a thorough research about {topic}
  expected_output: >
    A list with 10 bullet points of the most relevant information about {topic}
  agent: researcher
```

- La **clave** de la tarea debe coincidir con la usada en `self.tasks_config['<clave>']` de `crew.py`.
- Para escribir un archivo de salida se usa `output_file='report.md'` en el `Task(...)` de `crew.py` (no en el YAML).

---

## 6. Sintaxis de `tools/custom_tool.py`

Las herramientas heredan de `BaseTool`, definen un `args_schema` con Pydantic e implementan `_run`.

```python
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = "Clear description for what this tool is useful for."
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        return "tool output"
```

---

## 7. Sintaxis de `main.py`

- Es solo el runner local — **no** meter lógica de negocio aquí.
- Debe exponer las funciones `run()`, `train()`, `replay()`, `test()` (y `run_with_trigger()` si aplica).
- Importa el crew con: `from <nombre_proyecto>.crew import NombreDelCrew`.
- Los `inputs` (dict) alimentan los placeholders `{variable}` de los YAML.

---

## 8. `pyproject.toml`

- `name` = nombre del proyecto (snake_case), igual que el paquete en `src/`.
- `requires-python = ">=3.10,<3.14"`.
- Dependencia base: `crewai[tools]`.
- Sección `[project.scripts]` con `run_crew`, `train`, `replay`, `test` apuntando a `<nombre_proyecto>.main:<func>`.
- Sección `[tool.crewai]` con `type = "crew"`.

---

## 9. Checklist antes de dar por terminado un cambio

- [ ] ¿El archivo está en la ubicación canónica de la estructura (sección 2)?
- [ ] ¿Los agentes/tareas nuevos están declarados en los YAML **y** con su decorador en `crew.py`?
- [ ] ¿Las claves de `agents_config`/`tasks_config` coinciden entre `crew.py` y los YAML?
- [ ] ¿Se respetó el estilo de decoradores (`@agent`, `@task`, `@crew`, `@CrewBase`)?
- [ ] ¿No se agregó lógica de negocio en `main.py`?
- [ ] ¿El `.env` sigue fuera del control de versiones?
