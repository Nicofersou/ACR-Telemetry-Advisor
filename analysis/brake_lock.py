"""
brake_lock.py
-------------
Capa de Análisis — Detección de bloqueo de frenos y patinaje de tracción.

Algoritmos:
    BLOQUEO: caída brusca de velocidad angular en alguna rueda mientras el
             vehículo aún mantiene velocidad longitudinal alta.
    PATINAJE: velocidad angular de ruedas motrices supera la velocidad real
              del vehículo en más de un umbral definido.

TODO (Fase 4):
- Calibrar umbrales con datos reales de frenadas de ACR.
- Añadir detección de qué rueda específica bloquea (FL, FR, RL, RR).
"""

import numpy as np


BRAKE_LOCK_THRESHOLD = 0.85   # fracción de caída de velocidad angular para considerar bloqueo
TRACTION_SLIP_THRESHOLD = 0.20  # slip ratio para considerar patinaje de tracción


def detect_brake_lock(wheel_speeds: list[float], vehicle_speed: float,
                      brake_input: float) -> dict:
    """
    Detecta bloqueo de frenos en cualquier rueda.

    Parámetros
    ----------
    wheel_speeds  : lista [FL, FR, RL, RR] de velocidades angulares (rad/s)
    vehicle_speed : velocidad longitudinal del vehículo (m/s)
    brake_input   : posición del pedal de freno (0.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'locked_wheels' (list), 'severity' (0.0–1.0)
    """
    if vehicle_speed < 2.0 or brake_input < 0.1:
        return {"detected": False, "locked_wheels": [], "severity": 0.0}

    wheel_names = ["FL", "FR", "RL", "RR"]
    locked = []

    for i, speed in enumerate(wheel_speeds):
        if speed < vehicle_speed * (1.0 - BRAKE_LOCK_THRESHOLD):
            locked.append(wheel_names[i])

    severity = float(np.clip(len(locked) / 4.0, 0.0, 1.0))

    return {
        "detected": bool(locked),
        "locked_wheels": locked,
        "severity": severity
    }


def detect_traction_slip(wheel_speed_driven_avg: float, vehicle_speed: float,
                         throttle_input: float) -> dict:
    """
    Detecta patinaje de las ruedas motrices.

    Parámetros
    ----------
    wheel_speed_driven_avg : velocidad angular media de las ruedas motrices (rad/s)
    vehicle_speed          : velocidad longitudinal del vehículo (m/s)
    throttle_input         : posición del acelerador (0.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'slip_ratio' (float), 'severity' (0.0–1.0)
    """
    if vehicle_speed < 0.5 or throttle_input < 0.1:
        return {"detected": False, "slip_ratio": 0.0, "severity": 0.0}

    slip_ratio = (wheel_speed_driven_avg - vehicle_speed) / vehicle_speed
    detected = slip_ratio > TRACTION_SLIP_THRESHOLD
    severity = float(np.clip(slip_ratio / (TRACTION_SLIP_THRESHOLD * 3), 0.0, 1.0))

    return {
        "detected": detected,
        "slip_ratio": round(slip_ratio, 4),
        "severity": severity
    }

