"""
brake_lock.py
-------------
Capa de Análisis — Detección de bloqueo de frenos y patinaje de tracción.

Algoritmos:
    BLOQUEO: caída brusca de velocidad angular en alguna rueda mientras el
             vehículo aún mantiene velocidad longitudinal alta Y el freno
             está pisado. Umbral calibrado para rally en gravel.

    PATINAJE DE TRACCIÓN: velocidad angular de ruedas motrices supera la
             velocidad real del vehículo más de un umbral. En rally en gravel,
             un patinaje de hasta 0.40 en salida de curva es COMPLETAMENTE
             NORMAL. Se sube el umbral a 0.60 para detectar solo patinaje
             excesivo y problemático.

Umbrales anteriores (asfalto):
    BRAKE_LOCK_THRESHOLD    = 0.85  → mantenemos, el bloqueo total es siempre malo
    TRACTION_SLIP_THRESHOLD = 0.20  → demasiado bajo para gravel, subimos a 0.60
"""

import numpy as np


BRAKE_LOCK_THRESHOLD    = 0.85   # fracción de caída de velocidad angular para bloqueo
TRACTION_SLIP_THRESHOLD = 0.60   # slip ratio para considerar patinaje de tracción excesivo
MIN_SPEED_MS = 5.0               # mínimo 5 m/s (~18 km/h) para analizar bloqueo
MIN_SPEED_TRACTION_MS = 2.0      # mínimo 2 m/s para analizar patinaje


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
    # Solo analizar si hay frenada real y velocidad suficiente
    if vehicle_speed < MIN_SPEED_MS or brake_input < 0.15:
        return {"detected": False, "locked_wheels": [], "severity": 0.0}

    wheel_names = ["FL", "FR", "RL", "RR"]
    locked = []

    for i, speed in enumerate(wheel_speeds):
        # Una rueda está bloqueada si gira mucho más lento que la velocidad del coche
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
    Detecta patinaje excesivo de las ruedas motrices.

    En rally en gravel un slip de 0.3-0.5 es normal en salida de curva.
    Solo se marca como incidente si supera 0.60 (patinaje claramente excesivo).

    Parámetros
    ----------
    wheel_speed_driven_avg : velocidad angular media de las ruedas motrices (rad/s)
    vehicle_speed          : velocidad longitudinal del vehículo (m/s)
    throttle_input         : posición del acelerador (0.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'slip_ratio' (float), 'severity' (0.0–1.0)
    """
    if vehicle_speed < MIN_SPEED_TRACTION_MS or throttle_input < 0.15:
        return {"detected": False, "slip_ratio": 0.0, "severity": 0.0}

    slip_ratio = (wheel_speed_driven_avg - vehicle_speed) / vehicle_speed
    detected = slip_ratio > TRACTION_SLIP_THRESHOLD
    severity = float(np.clip(
        (slip_ratio - TRACTION_SLIP_THRESHOLD) / TRACTION_SLIP_THRESHOLD,
        0.0, 1.0
    ))

    return {
        "detected": detected,
        "slip_ratio": round(slip_ratio, 4),
        "severity": round(severity, 4),
    }

