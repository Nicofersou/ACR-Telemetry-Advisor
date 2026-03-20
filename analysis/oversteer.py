"""
oversteer.py
------------
Capa de Análisis — Detección de sobreviraje.

Algoritmo base:
    Las ruedas traseras superan la velocidad de referencia del vehículo,
    o el yaw rate medido supera el valor teórico para el radio de curva calculado.

TODO (Fase 4):
- Integrar el canal de yaw rate cuando esté disponible en la telemetría de ACR.
- Ajustar umbrales con datos reales.
"""

import numpy as np


OVERSTEER_SLIP_THRESHOLD = 0.12  # diferencia de slip ratio para considerar sobreviraje


def detect(wheel_speed_rl: float, wheel_speed_rr: float,
           vehicle_speed: float, steering_angle: float) -> dict:
    """
    Detecta sobreviraje comparando la velocidad de ruedas traseras con la del vehículo.

    Parámetros
    ----------
    wheel_speed_rl/rr : velocidad angular ruedas traseras (rad/s)
    vehicle_speed     : velocidad longitudinal del vehículo (m/s)
    steering_angle    : ángulo de volante normalizado (-1.0 a 1.0)

    Retorna
    -------
    dict con 'detected' (bool), 'severity' (0.0–1.0) y 'description' (str)
    """
    if vehicle_speed < 1.0:
        return {"detected": False, "severity": 0.0, "description": "Velocidad insuficiente"}

    rear_avg = (wheel_speed_rl + wheel_speed_rr) / 2.0
    slip_ratio = (rear_avg - vehicle_speed) / vehicle_speed if vehicle_speed > 0 else 0.0

    detected = slip_ratio > OVERSTEER_SLIP_THRESHOLD and abs(steering_angle) > 0.05
    severity = float(np.clip(slip_ratio / (OVERSTEER_SLIP_THRESHOLD * 3), 0.0, 1.0))

    return {
        "detected": detected,
        "severity": severity,
        "description": f"Slip trasero: {slip_ratio:.3f}" if detected else "Sin sobreviraje detectado"
    }

