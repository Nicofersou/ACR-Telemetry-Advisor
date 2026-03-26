"""
session_analyzer.py
-------------------
Capa de AnÃ¡lisis â€” Orquestador de sesiÃ³n completa. Fase 4 del proyecto.

Responsabilidad: recibir la lista completa de TelemetryFrames de una sesiÃ³n,
pasarlos por los detectores individuales (understeer, oversteer, brake_lock)
y producir un SessionReport con los resultados agregados listos para:
    - Mostrarse en la UI (Fase 6)
    - Enviarse al LLM para generar recomendaciones (Fase 5)

Flujo:
    TelemetryFrame[] â†’ SessionAnalyzer.analyze() â†’ SessionReport

ClasificaciÃ³n del sobreviraje:
    - 'oversteer_induced'     : tÃ©cnica de rally deliberada â†’ no se reporta como problema
    - 'oversteer_driver_error': pÃ©rdida de control puntual â†’ error del piloto
    - 'oversteer_setup'       : sobreviraje no-inducido persistente (>15% de frames
                                 en curva) â†’ posible problema de setup
"""

from dataclasses import dataclass, field
from typing import Optional

from models.telemetry_data import TelemetryFrame
from analysis import understeer, oversteer, brake_lock


# â”€â”€ Umbral para clasificar sobreviraje de setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Si mÃ¡s del 15% de los frames con volante girado tienen sobreviraje no-inducido,
# consideramos que hay un problema de setup (no solo errores puntuales del piloto).
SETUP_OVERSTEER_RATIO_THRESHOLD = 0.15


# â”€â”€â”€ Modelos de resultado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class IncidentRecord:
    """
    Registro de un Ãºnico incidente detectado durante la sesiÃ³n.

    incident_type puede ser:
        "understeer"           â€” subviraje de setup
        "oversteer_induced"    â€” sobreviraje inducido (tÃ©cnica de rally)
        "oversteer_driver_error" â€” sobreviraje no intencionado
        "oversteer_setup"      â€” sobreviraje de setup (detectado al final del anÃ¡lisis)
        "brake_lock"           â€” bloqueo de frenos
        "traction_slip"        â€” patinaje excesivo de tracciÃ³n
    """
    incident_type: str        # ver tipos arriba
    severity: float           # 0.0 â€“ 1.0
    stage_distance: float     # metros desde el inicio de la etapa
    timestamp: float          # epoch en segundos
    detail: str               # descripciÃ³n textual del incidente


@dataclass
class SessionReport:
    """
    Informe completo del anÃ¡lisis de una sesiÃ³n.

    Contiene tanto los incidentes individuales como los promedios globales
    que se usarÃ¡n para construir el prompt del LLM en la Fase 5.

    Novedad respecto a la versiÃ³n anterior:
        - pedal_data: lista de tuplas (distancia_km, throttle, brake) para la
          grÃ¡fica de pedales de la UI.
        - oversteer_setup_detected: flag que indica si se detectÃ³ sobreviraje
          de setup (no solo errores puntuales).
    """
    # Lista de todos los incidentes detectados, en orden temporal
    incidents: list[IncidentRecord] = field(default_factory=list)

    # Severidad media por tipo de comportamiento (0.0 â€“ 1.0)
    avg_understeer_severity: float = 0.0
    avg_oversteer_severity: float = 0.0
    avg_brake_lock_severity: float = 0.0
    avg_traction_slip_severity: float = 0.0

    # Totales de frames analizados e incidentes encontrados
    total_frames: int = 0
    total_incidents: int = 0

    # Distancia total de la etapa en metros
    stage_distance_m: float = 0.0

    # Superficie detectada (la mÃ¡s frecuente en los frames)
    surface: Optional[str] = None

    # â”€â”€ Datos para la grÃ¡fica de pedales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Lista de (distancia_km, throttle 0-1, brake 0-1) para el eje X compartido
    pedal_data: list[tuple] = field(default_factory=list)

    # â”€â”€ Flag de sobreviraje de setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    oversteer_setup_detected: bool = False
    oversteer_setup_ratio: float = 0.0   # fracciÃ³n de frames en curva con sobreviraje no-inducido

    def summary(self) -> str:
        """
        Devuelve un resumen en texto plano del informe.
        Ãštil para depuraciÃ³n y para construir el prompt del LLM.
        """
        oversteer_note = ""
        if self.oversteer_setup_detected:
            oversteer_note = (
                f"\n  âš  Sobreviraje de SETUP detectado "
                f"({self.oversteer_setup_ratio:.0%} de frames en curva)"
            )

        lines = [
            f"=== Informe de SesiÃ³n ===",
            f"Frames analizados : {self.total_frames}",
            f"Distancia de etapa: {self.stage_distance_m:.0f} m",
            f"Superficie        : {self.surface or 'desconocida'}",
            f"Total incidentes  : {self.total_incidents}",
            f"",
            f"Severidad media por comportamiento:",
            f"  Â· Subviraje      : {self.avg_understeer_severity:.2f}",
            f"  Â· Sobreviraje    : {self.avg_oversteer_severity:.2f}{oversteer_note}",
            f"  Â· Bloqueo frenos : {self.avg_brake_lock_severity:.2f}",
            f"  Â· Patinaje       : {self.avg_traction_slip_severity:.2f}",
        ]

        if self.incidents:
            lines.append(f"")
            lines.append(f"Primeros 5 incidentes:")
            for inc in self.incidents[:5]:
                lines.append(
                    f"  [{inc.incident_type:25s}] km {inc.stage_distance/1000:.2f} "
                    f"| severidad {inc.severity:.2f} | {inc.detail}"
                )

        return "\n".join(lines)


# â”€â”€â”€ Orquestador principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SessionAnalyzer:
    """
    Procesa una lista de TelemetryFrames y genera un SessionReport.

    Uso bÃ¡sico:
        analyzer = SessionAnalyzer()
        report = analyzer.analyze(frames)
        print(report.summary())
    """

    def analyze(self, frames: list[TelemetryFrame]) -> SessionReport:
        """
        Analiza la sesiÃ³n completa y devuelve el informe agregado.

        Recorre cada frame, aplica los tres detectores y acumula los
        resultados. Al final calcula las medias globales y determina
        si el sobreviraje es de setup.

        ParÃ¡metros
        ----------
        frames : list[TelemetryFrame]
            Lista ordenada de frames de la sesiÃ³n.

        Retorna
        -------
        SessionReport con todos los incidentes y mÃ©tricas agregadas.
        """
        report = SessionReport()
        report.total_frames = len(frames)

        # Acumuladores para calcular medias al final
        understeer_severities: list[float] = []
        oversteer_severities: list[float] = []
        brake_lock_severities: list[float] = []
        traction_slip_severities: list[float] = []

        # Contadores para sobreviraje de setup
        frames_in_corner = 0          # frames con volante > 8%
        frames_oversteer_non_induced = 0  # sobreviraje no-inducido en curva

        # Conteo de superficies para detectar la mÃ¡s frecuente
        surface_counts: dict[str, int] = {}

        for frame in frames:

            # â”€â”€ Datos de pedales para la grÃ¡fica â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            report.pedal_data.append((
                frame.stage_distance / 1000.0,  # km
                frame.throttle,
                frame.brake,
            ))

            # â”€â”€ Subviraje â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            us = understeer.detect(
                wheel_speed_fl=frame.wheel_speed_fl,
                wheel_speed_fr=frame.wheel_speed_fr,
                wheel_speed_rl=frame.wheel_speed_rl,
                wheel_speed_rr=frame.wheel_speed_rr,
                vehicle_speed=frame.vehicle_speed,
                steering_angle=frame.steering_angle,
                brake=frame.brake,
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

            # â”€â”€ Sobreviraje â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            os_result = oversteer.detect(
                wheel_speed_rl=frame.wheel_speed_rl,
                wheel_speed_rr=frame.wheel_speed_rr,
                vehicle_speed=frame.vehicle_speed,
                steering_angle=frame.steering_angle,
                throttle=frame.throttle,          # <-- nuevo: necesario para clasificar tipo
            )
            oversteer_severities.append(os_result["severity"])

            # Contamos frames en curva para el ratio de setup
            if abs(frame.steering_angle) >= 0.08:
                frames_in_corner += 1

            if os_result["detected"]:
                os_type = os_result["oversteer_type"]  # 'induced' | 'driver_error'

                # El sobreviraje inducido NO cuenta como sobreviraje de setup
                if os_type == "driver_error":
                    frames_oversteer_non_induced += 1

                # Registramos el incidente con el tipo correcto
                incident_type = (
                    "oversteer_induced"
                    if os_type == "induced"
                    else "oversteer_driver_error"
                )
                report.incidents.append(IncidentRecord(
                    incident_type=incident_type,
                    severity=os_result["severity"],
                    stage_distance=frame.stage_distance,
                    timestamp=frame.timestamp,
                    detail=os_result["description"],
                ))

            # â”€â”€ Bloqueo de frenos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            # â”€â”€ Patinaje de tracciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                    detail=f"Slip excesivo: {ts['slip_ratio']:.3f}",
                ))

            # â”€â”€ Superficie â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if frame.surface:
                surface_counts[frame.surface] = surface_counts.get(frame.surface, 0) + 1

        # â”€â”€ Calcular medias â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        report.avg_understeer_severity    = _safe_mean(understeer_severities)
        report.avg_oversteer_severity     = _safe_mean(oversteer_severities)
        report.avg_brake_lock_severity    = _safe_mean(brake_lock_severities)
        report.avg_traction_slip_severity = _safe_mean(traction_slip_severities)

        report.total_incidents = len(report.incidents)

        # Distancia total: el Ãºltimo frame tiene la distancia acumulada
        if frames:
            report.stage_distance_m = frames[-1].stage_distance

        # Superficie mÃ¡s frecuente
        if surface_counts:
            report.surface = max(surface_counts, key=surface_counts.get)

        # â”€â”€ Determinar sobreviraje de setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if frames_in_corner > 0:
            ratio = frames_oversteer_non_induced / frames_in_corner
            report.oversteer_setup_ratio = round(ratio, 4)
            if ratio >= SETUP_OVERSTEER_RATIO_THRESHOLD:
                report.oversteer_setup_detected = True
                # AÃ±adimos un incidente de resumen de tipo 'oversteer_setup'
                # al principio de la lista para que aparezca destacado
                report.incidents.insert(0, IncidentRecord(
                    incident_type="oversteer_setup",
                    severity=min(1.0, ratio * 2),
                    stage_distance=0.0,
                    timestamp=frames[0].timestamp if frames else 0.0,
                    detail=(
                        f"Sobreviraje no-inducido en {ratio:.0%} de frames en curva. "
                        f"Revisar ARB trasero, diferencial o presiÃ³n neumÃ¡ticos."
                    ),
                ))

        return report


# â”€â”€â”€ Utilidades internas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _safe_mean(values: list[float]) -> float:
    """Calcula la media de una lista. Devuelve 0.0 si la lista estÃ¡ vacÃ­a."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)

