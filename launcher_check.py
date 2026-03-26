"""
launcher_check.py
-----------------
Script de verificación previa al arranque de ACR Telemetry Advisor.

Comprueba que todas las dependencias críticas están instaladas y que
Ollama está en marcha (si está disponible).

Se invoca automáticamente desde ACR_Advisor.bat antes de lanzar main.py.
También puede ejecutarse manualmente:  python launcher_check.py
"""

import sys
import importlib
import subprocess
import urllib.request

# ─── Dependencias requeridas ──────────────────────────────────────────────────
# Cada entrada es (nombre_import, nombre_pip, crítico)
# crítico=True  → si falta, se aborta el arranque
# crítico=False → si falta, se avisa pero se continúa
REQUIRED = [
    ("PyQt6",      "PyQt6",      True),
    ("matplotlib", "matplotlib", True),
    ("numpy",      "numpy",      True),
    ("pandas",     "pandas",     True),
    ("ollama",     "ollama",     False),   # opcional: sin él no hay recomendaciones IA
]

OLLAMA_URL = "http://localhost:11434/api/tags"

# ─── Colores ANSI para la consola ─────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def check_dependencies() -> bool:
    """
    Verifica que todos los paquetes críticos están instalados.

    Retorna True si todo está bien, False si falta algo crítico.
    """
    print(f"{BOLD}  Dependencias de Python:{RESET}")
    all_ok = True

    for import_name, pip_name, critical in REQUIRED:
        try:
            importlib.import_module(import_name)
            print(f"  {GREEN}✔{RESET}  {pip_name}")
        except ImportError:
            if critical:
                print(f"  {RED}✘  {pip_name}  ← FALTA (crítico){RESET}")
                all_ok = False
            else:
                print(f"  {YELLOW}⚠  {pip_name}  ← no instalado (opcional){RESET}")

    return all_ok


def check_ollama() -> None:
    """
    Comprueba si Ollama está corriendo en localhost:11434.
    No es crítico — solo informa al usuario.
    """
    print(f"\n{BOLD}  Ollama (IA local):{RESET}")
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=2) as resp:
            if resp.status == 200:
                print(f"  {GREEN}✔{RESET}  Ollama está activo en localhost:11434")
            else:
                print(f"  {YELLOW}⚠{RESET}  Ollama responde pero con estado {resp.status}")
    except Exception:
        print(
            f"  {YELLOW}⚠{RESET}  Ollama no detectado en localhost:11434\n"
            f"       Las recomendaciones de setup no estarán disponibles.\n"
            f"       Para activarlas, abre Ollama antes de lanzar la app."
        )


def check_python_version() -> bool:
    """Verifica que la versión de Python es 3.11 o superior."""
    print(f"{BOLD}  Versión de Python:{RESET}")
    major, minor = sys.version_info.major, sys.version_info.minor
    version_str = f"{major}.{minor}.{sys.version_info.micro}"

    if major >= 3 and minor >= 11:
        print(f"  {GREEN}✔{RESET}  Python {version_str}")
        return True
    else:
        print(f"  {RED}✘  Python {version_str}  ← Se requiere 3.11 o superior{RESET}")
        return False


# ─── Punto de entrada ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()

    version_ok   = check_python_version()
    print()
    packages_ok  = check_dependencies()
    check_ollama()

    print()

    if not version_ok or not packages_ok:
        print(f"  {RED}{BOLD}Hay problemas que impiden arrancar la aplicación.{RESET}")
        print(f"  Ejecuta:  pip install -r requirements.txt")
        print()
        sys.exit(1)
    else:
        print(f"  {GREEN}{BOLD}Todo listo. Arrancando ACR Telemetry Advisor...{RESET}")
        print()
        sys.exit(0)

