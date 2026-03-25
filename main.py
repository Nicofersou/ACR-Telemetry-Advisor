"""
main.py
-------
Punto de entrada de ACR Telemetry Advisor.

Flujo actual (Fases 3 y 4 implementadas):
    1. [Fase 3] Conectar con TelemetryReader en modo mock.
    2. [Fase 3] Cargar los frames de la sesión simulada.
    3. [Fase 4] Pasar los frames al SessionAnalyzer.
    4. [Fase 4] Mostrar el informe de resultados.

Fases pendientes:
    5. [Fase 5] Enviar el SessionReport al SetupAdvisor (LLM).
    6. [Fase 6] Lanzar la interfaz gráfica principal.
"""

from capture.telemetry_reader import TelemetryReader
from capture.mock_data import generate_session_frames
from analysis.session_analyzer import SessionAnalyzer


def main():
    print("ACR Telemetry Advisor — iniciando...\n")

    # ── Fase 3: Captura ───────────────────────────────────────────────────────
    # En modo post-sesión cargamos todos los frames de golce (sin sleep).
    # iter_session(fps=60) se usará en Fase 6 para el panel en tiempo real.
    reader = TelemetryReader(mock=True)

    if not reader.connect():
        print("No se pudo conectar con la fuente de telemetría. Abortando.")
        return

    frames = generate_session_frames()
    reader.disconnect()

    print(f"Frames capturados: {len(frames)}\n")

    # ── Fase 4: Análisis ──────────────────────────────────────────────────────
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)

    print(report.summary())

    # ── Fases 5 y 6: pendientes ───────────────────────────────────────────────
    print("\n[Fase 5 — LLM] Pendiente: enviar informe a SetupAdvisor.")
    print("[Fase 6 — UI]  Pendiente: mostrar resultados en la interfaz gráfica.")


if __name__ == "__main__":
    main()
