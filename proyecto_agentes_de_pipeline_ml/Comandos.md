# Comandos

Ubícate en la carpeta del proyecto (la que tiene el `pyproject.toml`):

```bash
cd proyecto_agentes_de_pipeline_ml
```

## 1. Crear el entorno virtual

```bash
uv venv --prompt CrewAI-Pipeline-ML
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
```

Y ejecuta:

```bash
crewai run
```
