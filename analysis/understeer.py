"""
understeer.py
-------------
Capa de Análisis — Detección de subviraje.

Algoritmo:
    Las ruedas delanteras rotan más lento que las traseras mientras el piloto
    está girando el volante. Esto indica que el eje delantero está saturado
    (empujando recto en lugar de seguir la curva).

    En rally en gravel, diferencias pequeñas entre el eje delantero y trasero
    son ABSOLUTAMENTE NORMALES. El umbral previo (0.15) era demasiado bajo.
    Calibrado a 0.35 con datos reales de ACR.

    Adicionalmente, solo tiene sentido detectar subviraje cuando:
    - El piloto está girando el volante significativamente (>15% recorrido).
    - La velocidad es suficiente (>20 km/h).
    - No se está pisando el freno a fondo (un freno suave con curva es
      normal y no indica subviraje de setup).
"""

import numpy as np


# ── Umbrales calibrados para rally en gravel ──────────────────────────────────
UNDERSTEER_SLIP_THRESHOLD = 0.35    # diferencia normalizada eje delantero vs trasero
MIN_STEERING_ANGLE = 0.15           # volante al menos 15% → el piloto está en curva real
MIN_SPEED_KMH = 20.0                # mínimo 20 km/h para análisis significativo
BRAKE_IGNORE_THRESHOLD = 0.80       # si frena >80%, podría ser trail braking, no subviraje


def detect(wheel_speed_fl: float, wheel_speed_fr: float,
           wheel_speed_rl: float, wheel_speed_rr: float,
           vehicle_speed: float, steering_angle: float,
           brake: float = 0.0) -> dict:
    """
    Detecta subviraje a partir de las velocidades de rueda e inputs del piloto.

    Parámetros
    ----------
    wheel_speed_fl/fr : velocidad angular ruedas delanteras (rad/s)
    wheel_speed_rl/rr : velocidad angular ruedas traseras (rad/s)
    vehicle_speed     : velocidad longitudinal del vehículo (m/s)
    steering_angle    : ángulo de volante normalizado (-1.0 a 1.0)
    brake             : posición del pedal de freno (0.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'severity' (0.0–1.0), 'slip_diff' (float)
    y 'description' (str)
    """
    speed_kmh = vehicle_speed * 3.6

    if speed_kmh < MIN_SPEED_KMH:
        return {
            "detected": False, "severity": 0.0, "slip_diff": 0.0,
            "description": "Velocidad insuficiente para análisis"
        }

    # Sin volante girado no puede haber subviraje (el coche va recto intencionadamente)
    if abs(steering_angle) < MIN_STEERING_ANGLE:
        return {
            "detected": False, "severity": 0.0, "slip_diff": 0.0,
            "description": "Volante recto — no aplica subviraje"
        }

    # Si frena muy fuerte, es probable trail braking intencionado, no subviraje
    if brake >= BRAKE_IGNORE_THRESHOLD:
        return {
            "detected": False, "severity": 0.0, "slip_diff": 0.0,
            "description": "Frenada fuerte — posible trail braking, no subviraje"
        }

    front_avg = (wheel_speed_fl + wheel_speed_fr) / 2.0
    rear_avg  = (wheel_speed_rl + wheel_speed_rr) / 2.0

    if rear_avg <= 0:
        return {
            "detected": False, "severity": 0.0, "slip_diff": 0.0,
            "description": "Sin referencia trasera"
        }

    # slip_diff positivo → traseras más rápidas → el delantero no sigue la curva = subviraje
    slip_diff = (rear_avg - front_avg) / rear_avg

    detected = slip_diff > UNDERSTEER_SLIP_THRESHOLD
    severity  = float(np.clip(slip_diff / (UNDERSTEER_SLIP_THRESHOLD * 2.5), 0.0, 1.0))

    return {
        "detected": detected,
        "severity": round(severity, 4),
        "slip_diff": round(slip_diff, 4),
        "description": (
            f"Subviraje — diferencial eje delantera/trasera: {slip_diff:.3f}"
            if detected else f"Sin subviraje — slip_diff: {slip_diff:.3f}"
        ),
    }

