# Comandos

Ubícate en la carpeta del proyecto (la que tiene el `pyproject.toml`):

```bash
cd proyecto_b_agentes_con_tools_y_observabilidad
```

## 1. Crear el entorno virtual

```bash
uv venv --prompt CrewAI-Tools-Observabilidad
```

## 2. Activar el entorno virtual

```bash
source .venv/bin/activate
```

## 3. Instalar las dependencias

```bash
uv sync
```

## 4. Ejecutar el crew

Crea un archivo `.env` en esta carpeta con:

```bash
OPENAI_API_KEY=sk-...
MODEL=gpt-4.1
AGENTOPS_API_KEY=...
SERPER_API_KEY=...
```

Y ejecuta:

```bash
crewai run
```
