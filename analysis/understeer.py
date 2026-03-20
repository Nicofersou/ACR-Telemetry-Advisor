"""
understeer.py
-------------
Capa de Análisis — Detección de subviraje.

Algoritmo base:
    Las ruedas delanteras rotan más lento de lo esperado dado el ángulo de volante.
    Se compara el slip angle estimado del eje delantero vs trasero mediante
    el diferencial de velocidades angulares de cada rueda.

TODO (Fase 4):
- Ajustar los umbrales con datos reales de sesiones de ACR.
- Añadir segmentación por tramos de etapa.
"""

import numpy as np


UNDERSTEER_SLIP_THRESHOLD = 0.15  # diferencia de slip ratio para considerar subviraje


def detect(wheel_speed_fl: float, wheel_speed_fr: float,
           wheel_speed_rl: float, wheel_speed_rr: float,
           vehicle_speed: float, steering_angle: float) -> dict:
    """
    Detecta subviraje a partir de las velocidades de rueda e inputs del piloto.

    Parámetros
    ----------
    wheel_speed_fl/fr : velocidad angular ruedas delanteras (rad/s)
    wheel_speed_rl/rr : velocidad angular ruedas traseras (rad/s)
    vehicle_speed     : velocidad longitudinal del vehículo (m/s)
    steering_angle    : ángulo de volante normalizado (-1.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'severity' (0.0–1.0) y 'description' (str)
    """
    if vehicle_speed < 1.0:
        return {"detected": False, "severity": 0.0, "description": "Velocidad insuficiente"}

    front_avg = (wheel_speed_fl + wheel_speed_fr) / 2.0
    rear_avg = (wheel_speed_rl + wheel_speed_rr) / 2.0

    if rear_avg == 0:
        return {"detected": False, "severity": 0.0, "description": "Sin referencia trasera"}

    slip_diff = (rear_avg - front_avg) / rear_avg

    detected = slip_diff > UNDERSTEER_SLIP_THRESHOLD and abs(steering_angle) > 0.1
    severity = float(np.clip(slip_diff / (UNDERSTEER_SLIP_THRESHOLD * 3), 0.0, 1.0))

    return {
        "detected": detected,
        "severity": severity,
        "description": f"Slip diferencial: {slip_diff:.3f}" if detected else "Sin subviraje detectado"
    }

