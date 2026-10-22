import ast
import glob
import json
import os
import re
import sys
from importlib import metadata
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


# Módulos cuyo nombre de import no coincide con el nombre del paquete en PyPI
IMPORT_A_PAQUETE = {
    "sklearn": "scikit-learn",
    "feature_engine": "feature-engine",
    "yaml": "pyyaml",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "skimage": "scikit-image",
    "dateutil": "python-dateutil",
}


class RequirementsScannerInput(BaseModel):
    """Input schema para RequirementsScannerTool."""
    folder_path: str = Field(..., description="Carpeta que contiene los notebooks (.ipynb) y scripts (.py) a escanear.")


class RequirementsScannerTool(BaseTool):
    name: str = "Requirements Scanner Tool"
    description: str = (
        "Escanea todos los notebooks (.ipynb) y scripts (.py) de una carpeta, extrae "
        "los imports de terceros (excluye la librería estándar y los módulos locales) y "
        "retorna, para cada paquete, su nombre en PyPI, la versión instalada en este "
        "entorno (si existe) y los archivos que lo usan."
    )
    args_schema: Type[BaseModel] = RequirementsScannerInput

    def _run(self, folder_path: str) -> str:
        if not os.path.isdir(folder_path):
            return f"Error: la carpeta '{folder_path}' no existe."

        archivos = sorted(
            glob.glob(os.path.join(folder_path, "*.ipynb"))
            + glob.glob(os.path.join(folder_path, "*.py"))
        )
        if not archivos:
            return f"No se encontraron notebooks ni scripts en '{folder_path}'."

        locales = {os.path.splitext(os.path.basename(a))[0] for a in archivos if a.endswith(".py")}
        locales |= {d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))}

        usos: dict[str, set[str]] = {}
        obligatorios: set[str] = set()
        errores = []
        for archivo in archivos:
            try:
                bloques = self._extraer_codigo(archivo)
            except Exception as e:
                errores.append(f"- {os.path.basename(archivo)}: {e}")
                continue
            for bloque in bloques:
                requeridos, opcionales = self._extraer_imports(bloque)
                for modulo in requeridos | opcionales:
                    if modulo in sys.stdlib_module_names or modulo in locales:
                        continue
                    usos.setdefault(modulo, set()).add(os.path.basename(archivo))
                    if modulo in requeridos:
                        obligatorios.add(modulo)

        lineas = [f"## Paquetes de terceros usados en {folder_path} ({len(archivos)} archivos)\n"]
        for modulo in sorted(usos, key=str.lower):
            paquete = IMPORT_A_PAQUETE.get(modulo, modulo)
            try:
                version = metadata.version(paquete)
            except metadata.PackageNotFoundError:
                version = "no instalado en este entorno"
            # Opcional = solo se importa dentro de un try/except ImportError
            tipo = "obligatorio" if modulo in obligatorios else "OPCIONAL (try/except ImportError)"
            lineas.append(
                f"- import `{modulo}` -> paquete `{paquete}` | {tipo} | versión local: {version} | "
                f"usado en: {', '.join(sorted(usos[modulo]))}"
            )
        if errores:
            lineas.append("\n## Archivos que no se pudieron analizar")
            lineas.extend(errores)
        return "\n".join(lineas)

    def sentencias_import(self, folder_path: str) -> list[str]:
        """Sentencias import obligatorias de terceros (ej. 'from pycaret.regression import setup'), sin duplicados."""
        archivos = sorted(
            glob.glob(os.path.join(folder_path, "*.ipynb"))
            + glob.glob(os.path.join(folder_path, "*.py"))
        )
        locales = {os.path.splitext(os.path.basename(a))[0] for a in archivos if a.endswith(".py")}
        sentencias: list[str] = []
        for archivo in archivos:
            for bloque in self._extraer_codigo(archivo):
                try:
                    arbol = ast.parse(bloque)
                except SyntaxError:
                    continue
                opcionales_ids = self._ids_opcionales(arbol)
                for nodo in ast.walk(arbol):
                    if id(nodo) in opcionales_ids:
                        continue
                    if isinstance(nodo, ast.Import):
                        raiz = nodo.names[0].name.split(".")[0]
                    elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                        raiz = nodo.module.split(".")[0]
                    else:
                        continue
                    sentencia = ast.unparse(nodo)
                    if raiz not in sys.stdlib_module_names and raiz not in locales and sentencia not in sentencias:
                        sentencias.append(sentencia)
        return sentencias

    def _extraer_codigo(self, archivo: str) -> list[str]:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
        if not archivo.endswith(".ipynb"):
            return [contenido]
        celdas = json.loads(contenido).get("cells", [])
        bloques = []
        for celda in celdas:
            if celda.get("cell_type") != "code":
                continue
            fuente = celda.get("source", [])
            texto = "".join(fuente) if isinstance(fuente, list) else fuente
            # Quita magics (%matplotlib, !pip) que no son Python válido
            bloques.append("\n".join(l for l in texto.splitlines() if not l.lstrip().startswith(("%", "!"))))
        return bloques

    def _extraer_imports(self, codigo: str) -> tuple[set[str], set[str]]:
        """Retorna (imports obligatorios, imports opcionales)."""
        try:
            arbol = ast.parse(codigo)
        except SyntaxError:
            # Celda con código inválido: se rescatan los imports línea por línea
            patron = r"^\s*(?:import|from)\s+([A-Za-z_]\w*)"
            return set(re.findall(patron, codigo, flags=re.MULTILINE)), set()

        opcionales_ids = self._ids_opcionales(arbol)
        requeridos, opcionales = set(), set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres = {alias.name.split(".")[0] for alias in nodo.names}
            elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                nombres = {nodo.module.split(".")[0]}
            else:
                continue
            (opcionales if id(nodo) in opcionales_ids else requeridos).update(nombres)
        return requeridos, opcionales

    def _ids_opcionales(self, arbol: ast.AST) -> set[int]:
        """Nodos que están dentro de un try/except ImportError (imports opcionales)."""
        ids = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Try) and any(self._captura_import_error(h) for h in nodo.handlers):
                for hijo in nodo.body:
                    ids.update(id(n) for n in ast.walk(hijo))
        return ids

    def _captura_import_error(self, handler: ast.ExceptHandler) -> bool:
        if handler.type is None:
            return True
        tipos = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        return any(isinstance(t, ast.Name) and t.id in ("ImportError", "ModuleNotFoundError") for t in tipos)
