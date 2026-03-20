"""
telemetry_data.py
-----------------
Modelo de datos central del proyecto.

TelemetryFrame representa un instante de telemetría leído desde ACR.
Es la estructura que fluye entre la capa de Captura, Análisis e Interfaz.

Campos alineados con los canales disponibles en la memoria compartida de ACR:
    - Velocidades angulares de las 4 ruedas
    - Velocidad longitudinal del vehículo
    - Aceleraciones (G)
    - Inputs del piloto
    - Posición en la etapa
    - Timestamp
"""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class TelemetryFrame:
    """Un instante de telemetría capturado desde ACR."""

    # --- Timestamp ---
    timestamp: float = field(default_factory=time.time)   # epoch en segundos

    # --- Velocidades angulares de ruedas (rad/s) ---
    wheel_speed_fl: float = 0.0   # delantera izquierda
    wheel_speed_fr: float = 0.0   # delantera derecha
    wheel_speed_rl: float = 0.0   # trasera izquierda
    wheel_speed_rr: float = 0.0   # trasera derecha

    # --- Velocidad del vehículo ---
    vehicle_speed: float = 0.0    # velocidad longitudinal (m/s)

    # --- Aceleraciones (G) ---
    lateral_g: float = 0.0        # aceleración lateral
    longitudinal_g: float = 0.0   # aceleración longitudinal

    # --- Inputs del piloto ---
    steering_angle: float = 0.0   # ángulo de volante normalizado (-1.0 a 1.0)
    throttle: float = 0.0         # posición acelerador (0.0 a 1.0)
    brake: float = 0.0            # posición freno (0.0 a 1.0)

    # --- Posición en la etapa ---
    stage_distance: float = 0.0   # distancia recorrida en la etapa (metros)

    # --- Metadatos opcionales ---
    surface: Optional[str] = None  # "gravel", "tarmac", "snow", "mixed"

    def to_dict(self) -> dict:
        """Convierte el frame a diccionario para serialización a CSV/JSON."""
        return {
            "timestamp": self.timestamp,
            "wheel_speed_fl": self.wheel_speed_fl,
            "wheel_speed_fr": self.wheel_speed_fr,
            "wheel_speed_rl": self.wheel_speed_rl,
            "wheel_speed_rr": self.wheel_speed_rr,
            "vehicle_speed": self.vehicle_speed,
            "lateral_g": self.lateral_g,
            "longitudinal_g": self.longitudinal_g,
            "steering_angle": self.steering_angle,
            "throttle": self.throttle,
            "brake": self.brake,
            "stage_distance": self.stage_distance,
            "surface": self.surface,
        }

