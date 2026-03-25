"""
main.py
-------
Punto de entrada de ACR Telemetry Advisor.

Fases implementadas:
    3. Captura de telemetría (mock)
    4. Análisis de sesión
    5. Recomendaciones con Ollama
    6. Interfaz gráfica con PyQt6  ← ACTIVO
"""

from ui.main_window import launch

if __name__ == "__main__":
    launch()
