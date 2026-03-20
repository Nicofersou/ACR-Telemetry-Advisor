"""
main.py
-------
Punto de entrada de ACR Telemetry Advisor.

Flujo principal (a implementar por fases):
    1. [Fase 3] Conectar con la memoria compartida de ACR.
    2. [Fase 3] Iniciar el bucle de captura de telemetría.
    3. [Fase 4] Pasar los frames al motor de análisis.
    4. [Fase 5] Enviar el diagnóstico al SetupAdvisor (LLM).
    5. [Fase 6] Lanzar la interfaz gráfica principal.
"""


def main():
    print("ACR Telemetry Advisor — iniciando...")
    print("Proyecto en configuración. Fases pendientes: 3 (captura), 4 (análisis), 5 (LLM), 6 (UI).")


if __name__ == "__main__":
    main()
