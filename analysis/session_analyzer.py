"""
session_analyzer.py
-------------------
Capa de Análisis — Orquestador de sesión completa. Fase 4 del proyecto.

Responsabilidad: recibir la lista completa de TelemetryFrames de una sesión,
pasarlos por los detectores individuales (understeer, oversteer, brake_lock)
y producir un SessionReport con los resultados agregados listos para:
    - Mostrarse en la UI (Fase 6)
    - Enviarse al LLM para generar recomendaciones (Fase 5)

Flujo:
    TelemetryFrame[] → SessionAnalyzer.analyze() → SessionReport
"""

from dataclasses import dataclass, field
from typing import Optional

from models.telemetry_data import TelemetryFrame
from analysis import understeer, oversteer, brake_lock


# ─── Modelos de resultado ─────────────────────────────────────────────────────

@dataclass
class IncidentRecord:
    """
    Registro de un único incidente detectado durante la sesión.

    Un 'incidente' es un frame concreto donde se ha detectado un comportamiento
    problemático: subviraje, sobreviraje, bloqueo de freno o patinaje.
    """
    incident_type: str        # "understeer" | "oversteer" | "brake_lock" | "traction_slip"
    severity: float           # 0.0 – 1.0
    stage_distance: float     # metros desde el inicio de la etapa
    timestamp: float          # epoch en segundos
    detail: str               # descripción textual del incidente


@dataclass
class SessionReport:
    """
    Informe completo del análisis de una sesión.

    Contiene tanto los incidentes individuales como los promedios globales
    que se usarán para construir el prompt del LLM en la Fase 5.
    """
    # Lista de todos los incidentes detectados, en orden temporal
    incidents: list[IncidentRecord] = field(default_factory=list)

    # Severidad media por tipo de comportamiento (0.0 – 1.0)
    avg_understeer_severity: float = 0.0
    avg_oversteer_severity: float = 0.0
    avg_brake_lock_severity: float = 0.0
    avg_traction_slip_severity: float = 0.0

    # Totales de frames analizados e incidentes encontrados
    total_frames: int = 0
    total_incidents: int = 0

    # Distancia total de la etapa en metros
    stage_distance_m: float = 0.0

    # Superficie detectada (la más frecuente en los frames)
    surface: Optional[str] = None

    def summary(self) -> str:
        """
        Devuelve un resumen en texto plano del informe.
        Útil para depuración y para construir el prompt del LLM.
        """
        lines = [
            f"=== Informe de Sesión ===",
            f"Frames analizados : {self.total_frames}",
            f"Distancia de etapa: {self.stage_distance_m:.0f} m",
            f"Superficie        : {self.surface or 'desconocida'}",
            f"Total incidentes  : {self.total_incidents}",
            f"",
            f"Severidad media por comportamiento:",
            f"  · Subviraje      : {self.avg_understeer_severity:.2f}",
            f"  · Sobreviraje    : {self.avg_oversteer_severity:.2f}",
            f"  · Bloqueo frenos : {self.avg_brake_lock_severity:.2f}",
            f"  · Patinaje       : {self.avg_traction_slip_severity:.2f}",
        ]

        if self.incidents:
            lines.append(f"")
            lines.append(f"Primeros 5 incidentes:")
            for inc in self.incidents[:5]:
                lines.append(
                    f"  [{inc.incident_type:15s}] km {inc.stage_distance/1000:.2f} "
                    f"| severidad {inc.severity:.2f} | {inc.detail}"
                )

        return "\n".join(lines)


# ─── Orquestador principal ────────────────────────────────────────────────────

class SessionAnalyzer:
    """
    Procesa una lista de TelemetryFrames y genera un SessionReport.

    Uso básico:
        analyzer = SessionAnalyzer()
        report = analyzer.analyze(frames)
        print(report.summary())
    """

    def analyze(self, frames: list[TelemetryFrame]) -> SessionReport:
        """
        Analiza la sesión completa y devuelve el informe agregado.

        Recorre cada frame, aplica los tres detectores y acumula los
        resultados. Al final calcula las medias globales.

        Parámetros
        ----------
        frames : list[TelemetryFrame]
            Lista ordenada de frames de la sesión, tal como la entrega
            TelemetryReader.iter_session() o generate_session_frames().

        Retorna
        -------
        SessionReport con todos los incidentes y métricas agregadas.
        """
        report = SessionReport()
        report.total_frames = len(frames)

        # Acumuladores para calcular medias al final
        understeer_severities: list[float] = []
        oversteer_severities: list[float] = []
        brake_lock_severities: list[float] = []
        traction_slip_severities: list[float] = []

        # Conteo de superficies para detectar la más frecuente
        surface_counts: dict[str, int] = {}

        for frame in frames:

            # ── Subviraje ──────────────────────────────────────────────────
            us = understeer.detect(
                wheel_speed_fl=frame.wheel_speed_fl,
                wheel_speed_fr=frame.wheel_speed_fr,
                wheel_speed_rl=frame.wheel_speed_rl,
                wheel_speed_rr=frame.wheel_speed_rr,
                vehicle_speed=frame.vehicle_speed,
                steering_angle=frame.steering_angle,
            )
            understeer_severities.append(us["severity"])
            if us["detected"]:
                report.incidents.append(IncidentRecord(
                    incident_type="understeer",
                    severity=us["severity"],
                    stage_distance=frame.stage_distance,
                    timestamp=frame.timestamp,
                    detail=us["description"],
                ))

            # ── Sobreviraje ────────────────────────────────────────────────
            os_result = oversteer.detect(
                wheel_speed_rl=frame.wheel_speed_rl,
                wheel_speed_rr=frame.wheel_speed_rr,
                vehicle_speed=frame.vehicle_speed,
                steering_angle=frame.steering_angle,
            )
            oversteer_severities.append(os_result["severity"])
            if os_result["detected"]:
                report.incidents.append(IncidentRecord(
                    incident_type="oversteer",
                    severity=os_result["severity"],
                    stage_distance=frame.stage_distance,
                    timestamp=frame.timestamp,
                    detail=os_result["description"],
                ))

            # ── Bloqueo de frenos ──────────────────────────────────────────
            bl = brake_lock.detect_brake_lock(
                wheel_speeds=[
                    frame.wheel_speed_fl,
                    frame.wheel_speed_fr,
                    frame.wheel_speed_rl,
                    frame.wheel_speed_rr,
                ],
                vehicle_speed=frame.vehicle_speed,
                brake_input=frame.brake,
            )
            brake_lock_severities.append(bl["severity"])
            if bl["detected"]:
                report.incidents.append(IncidentRecord(
                    incident_type="brake_lock",
                    severity=bl["severity"],
                    stage_distance=frame.stage_distance,
                    timestamp=frame.timestamp,
                    detail=f"Ruedas bloqueadas: {', '.join(bl['locked_wheels'])}",
                ))

            # ── Patinaje de tracción ───────────────────────────────────────
            driven_avg = (frame.wheel_speed_rl + frame.wheel_speed_rr) / 2.0
            ts = brake_lock.detect_traction_slip(
                wheel_speed_driven_avg=driven_avg,
                vehicle_speed=frame.vehicle_speed,
                throttle_input=frame.throttle,
            )
            traction_slip_severities.append(ts["severity"])
            if ts["detected"]:
                report.incidents.append(IncidentRecord(
                    incident_type="traction_slip",
                    severity=ts["severity"],
                    stage_distance=frame.stage_distance,
                    timestamp=frame.timestamp,
                    detail=f"Slip ratio: {ts['slip_ratio']:.3f}",
                ))

            # ── Superficie ────────────────────────────────────────────────
            if frame.surface:
                surface_counts[frame.surface] = surface_counts.get(frame.surface, 0) + 1

        # ── Calcular medias ────────────────────────────────────────────────
        report.avg_understeer_severity   = _safe_mean(understeer_severities)
        report.avg_oversteer_severity    = _safe_mean(oversteer_severities)
        report.avg_brake_lock_severity   = _safe_mean(brake_lock_severities)
        report.avg_traction_slip_severity = _safe_mean(traction_slip_severities)

        report.total_incidents = len(report.incidents)

        # Distancia total: el último frame tiene la distancia acumulada
        if frames:
            report.stage_distance_m = frames[-1].stage_distance

        # Superficie más frecuente
        if surface_counts:
            report.surface = max(surface_counts, key=surface_counts.get)

        return report


# ─── Utilidades internas ──────────────────────────────────────────────────────

def _safe_mean(values: list[float]) -> float:
    """Calcula la media de una lista. Devuelve 0.0 si la lista está vacía."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)

