import json
import os
import re
import shutil
import subprocess
import tempfile
from crewai.tools import BaseTool
from typing import Any, Type
from pydantic import BaseModel, Field

from proyecto_agentes_de_pipeline_ml.tools.requirements_scanner_tool import RequirementsScannerTool


# Versiones de Python contra las que se valida el requirements.txt
# (PyCaret 3.3.x solo soporta Python 3.9-3.11: en 3.12 se instala pero falla al importarse)
VERSIONES_PYTHON = ("3.11",)

# Paquetes que se muestran en el resumen de la resolución
PAQUETES_CLAVE = {
    "pandas", "numpy", "scipy", "scikit-learn", "feature-engine", "joblib",
    "matplotlib", "seaborn", "pycaret", "lightgbm", "xgboost", "catboost",
    "statsmodels", "sktime", "ipykernel",
}

# Nombres de import que NO deben ir en un requirements.txt (paquetes vacíos o deprecados en PyPI)
NOMBRES_INVALIDOS = {"sklearn": "scikit-learn", "feature_engine": "feature-engine"}

# Se ejecuta DENTRO del entorno temporal: corre cada import de los notebooks y clasifica los fallos.
# - "notebook": el nombre existe en el paquete instalado pero en otra ruta (error del notebook).
# - "bloqueante": el paquete o el nombre no existe en esa versión, o falla una dependencia interna.
SCRIPT_PRUEBA_IMPORTS = r'''
import ast, importlib.util, json, os, re, sys

def existe_en_paquete(raiz, nombre):
    spec = importlib.util.find_spec(raiz)
    if spec is None or not spec.submodule_search_locations:
        return False
    patron = re.compile(rf"^\s*(class|def)\s+{re.escape(nombre)}\b|^{re.escape(nombre)}\s*=", re.MULTILINE)
    for carpeta in spec.submodule_search_locations:
        for base, _, archivos in os.walk(carpeta):
            for archivo in archivos:
                if archivo.endswith(".py"):
                    with open(os.path.join(base, archivo), encoding="utf-8", errors="ignore") as f:
                        if patron.search(f.read()):
                            return True
    return False

fallos = []
for sentencia in json.load(open(sys.argv[1])):
    try:
        exec(sentencia, {})
        continue
    except Exception as e:
        error = e
    nodo = ast.parse(sentencia).body[0]
    modulo = nodo.module if isinstance(nodo, ast.ImportFrom) else nodo.names[0].name
    raiz = modulo.split(".")[0]
    nombres = [a.name for a in nodo.names] if isinstance(nodo, ast.ImportFrom) else []
    tipo = "bloqueante"
    modulo_error = getattr(error, "name", None) or ""
    es_ruta_propia = (
        isinstance(error, ImportError)
        and modulo_error.split(".")[0] == raiz
        and modulo_error != raiz
        and (modulo_error == modulo or modulo_error.startswith(modulo + "."))
    )
    if es_ruta_propia and nombres:
        faltantes = [n for n in nombres if n in str(error)] or nombres
        if all(existe_en_paquete(raiz, n) for n in faltantes):
            tipo = "notebook"
    fallos.append({"sentencia": sentencia, "tipo": tipo, "error": f"{type(error).__name__}: {error}"[:300]})
print(json.dumps(fallos))
'''


def validar_resolucion(requirements: str, python_version: str) -> tuple[bool, str, dict[str, str]]:
    """Resuelve el requirements con 'uv pip compile'. Retorna (es_instalable, mensaje, versiones_resueltas)."""
    if shutil.which("uv") is None:
        return False, "Error: 'uv' no está instalado; no se puede validar la resolución.", {}

    for linea in requirements.splitlines():
        nombre = re.split(r"[<>=!~\[;\s#]", linea.strip(), maxsplit=1)[0]
        if nombre in NOMBRES_INVALIDOS:
            return False, (
                f"CONFLICTO: '{nombre}' es el nombre del import, no del paquete. "
                f"Usa '{NOMBRES_INVALIDOS[nombre]}'."
            ), {}

    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "requirements.in")
        with open(entrada, "w", encoding="utf-8") as f:
            f.write(requirements)
        try:
            resultado = subprocess.run(
                ["uv", "pip", "compile", entrada, "--python-version", python_version,
                 "--no-header", "--no-annotate", "--quiet"],
                capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            return False, "Error: la resolución tardó más de 180 segundos.", {}

    if resultado.returncode != 0:
        return False, f"CONFLICTO (Python {python_version}): no se puede instalar.\n{resultado.stderr.strip()}", {}

    resueltos = [l for l in resultado.stdout.splitlines() if l and not l.startswith("#")]
    clave = [l for l in resueltos if l.split("==")[0].lower() in PAQUETES_CLAVE]
    versiones = dict(l.split(" ")[0].split("==", 1) for l in resueltos if "==" in l)
    return True, (
        f"OK (Python {python_version}): instalable, {len(resueltos)} paquetes en total.\n"
        "Versiones resueltas de los paquetes principales:\n" + "\n".join(clave)
    ), versiones


def validar_instalacion(requirements: str, python_version: str, folder_path: str) -> tuple[bool, str]:
    """Resuelve, instala en un entorno temporal y ejecuta los imports de los notebooks. Retorna (es_valido, reporte)."""
    ok, mensaje, versiones = validar_resolucion(requirements, python_version)
    if not ok:
        return False, mensaje

    sentencias = RequirementsScannerTool().sentencias_import(folder_path)
    with tempfile.TemporaryDirectory() as tmp:
        entorno = os.path.join(tmp, "venv")
        python = os.path.join(entorno, "bin", "python")
        archivo_req = os.path.join(tmp, "requirements.txt")
        archivo_imports = os.path.join(tmp, "imports.json")
        archivo_script = os.path.join(tmp, "probar_imports.py")
        with open(archivo_req, "w", encoding="utf-8") as f:
            f.write(requirements)
        with open(archivo_imports, "w", encoding="utf-8") as f:
            json.dump(sentencias, f)
        with open(archivo_script, "w", encoding="utf-8") as f:
            f.write(SCRIPT_PRUEBA_IMPORTS)

        try:
            for comando in (
                ["uv", "venv", "--quiet", "--python", python_version, entorno],
                ["uv", "pip", "install", "--quiet", "--python", python, "-r", archivo_req],
            ):
                paso = subprocess.run(comando, capture_output=True, text=True, timeout=900)
                if paso.returncode != 0:
                    return False, f"CONFLICTO (Python {python_version}): falla la instalación.\n{paso.stderr.strip()[-1500:]}"
            prueba = subprocess.run(
                [python, "-I", archivo_script, archivo_imports],
                capture_output=True, text=True, timeout=600, cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return False, f"Error (Python {python_version}): la instalación o la prueba de imports superó el tiempo límite."

    try:
        fallos = json.loads(prueba.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return False, f"Error (Python {python_version}): no se pudo ejecutar la prueba de imports.\n{prueba.stderr.strip()[-1500:]}"

    bloqueantes = [f for f in fallos if f["tipo"] == "bloqueante"]
    del_notebook = [f for f in fallos if f["tipo"] == "notebook"]
    reporte = [mensaje.replace("instalable", "instalado", 1), f"Imports probados: {len(sentencias)}."]
    if bloqueantes:
        reporte[0] = f"CONFLICTO (Python {python_version}): se instala, pero los notebooks NO pueden importar sus paquetes."
        reporte.append("Imports que fallan por versiones incompatibles:")
        reporte.extend(f"- {f['sentencia']} -> {f['error']}" for f in bloqueantes)
    if del_notebook:
        reporte.append("Advertencias (errores de ruta en el notebook, no del requirements):")
        reporte.extend(f"- {f['sentencia']} -> {f['error']}" for f in del_notebook)
    if not bloqueantes:
        # Rangos ~= (compatible release) construidos con lo que realmente se instaló y funcionó
        directos = [re.split(r"[<>=!~\[;\s#]", l.strip(), maxsplit=1)[0] for l in requirements.splitlines()]
        sugeridos = [
            f"{n}~={versiones[n.lower()]}" for n in directos
            if n and not n.startswith("#") and n.lower() in versiones
        ]
        reporte.append("Bloque de dependencias sugerido (versiones validadas, cópialo tal cual):")
        reporte.extend(sugeridos)
    return not bloqueantes, "\n".join(reporte)


def guardrail_requirements(resultado: Any, folder_path: str) -> tuple[bool, Any]:
    """Guardrail de la tarea: solo acepta un requirements.txt que instale y cuyos imports funcionen en todas las VERSIONES_PYTHON."""
    contenido = re.sub(r"^```[a-z]*\s*$", "", resultado.raw.strip(), flags=re.MULTILINE).strip()
    for version in VERSIONES_PYTHON:
        ok, reporte = validar_instalacion(contenido, version, folder_path)
        if not ok:
            return False, (
                f"El requirements.txt entregado NO es válido.\n{reporte}\n"
                "Corrige los rangos de versión, valídalo con el Requirements Validator Tool "
                f"en Python {' y '.join(VERSIONES_PYTHON)} y entrega de nuevo el archivo completo."
            )
    return True, contenido + "\n"


class RequirementsValidatorInput(BaseModel):
    """Input schema para RequirementsValidatorTool."""
    requirements: str = Field(..., description="Contenido propuesto del requirements.txt (una dependencia por línea).")
    folder_path: str = Field(..., description="Carpeta de los notebooks cuyos imports se deben probar.")
    python_version: str = Field("3.11", description="Versión de Python contra la que se valida (ej. '3.11', '3.12').")


class RequirementsValidatorTool(BaseTool):
    name: str = "Requirements Validator Tool"
    description: str = (
        "Valida un requirements.txt propuesto: resuelve las dependencias con uv, las "
        "instala en un entorno temporal de la versión de Python indicada y ejecuta los "
        "imports reales de los notebooks de la carpeta. Retorna OK con las versiones "
        "instaladas, o CONFLICTO con el paquete o import que falla."
    )
    args_schema: Type[BaseModel] = RequirementsValidatorInput

    def _run(self, requirements: str, folder_path: str, python_version: str = "3.11") -> str:
        return validar_instalacion(requirements, python_version, folder_path)[1]
