# Comandos

Ubícate en la carpeta del proyecto (la que tiene el `pyproject.toml`):

```bash
cd proyecto_b_agentes_con_tools_y_observabilidad
```

## 1. Crear el entorno virtual

```bash
uv venv --prompt CrewAI-Tools-Observabilidad

o

conda create -n CrewAI-Agentes python=3.12
```

## 2. Activar el entorno virtual

```bash
source .venv/bin/activate

o

conda activate CrewAI-Agentes
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
SERPER_API_KEY=...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Y ejecuta:

```bash
crewai run
```
