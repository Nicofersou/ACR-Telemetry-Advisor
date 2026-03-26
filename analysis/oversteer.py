"""
oversteer.py
------------
Capa de Análisis — Detección y clasificación de sobreviraje.

Algoritmo:
    El sobreviraje se detecta cuando las ruedas traseras superan
    significativamente la velocidad del vehículo MIENTRAS se está girando
    (steering_angle alto). Se distinguen tres tipos:

    1. INDUCIDO (induced):  El piloto pisa gas a fondo con volante girado.
       En rally es una técnica deliberada para rotar el coche. No es un error.

    2. ERROR (driver_error): Ocurre sin aceleración fuerte, con bajo input de
       volante. El piloto perdió el control de la trasera. Error de conducción.

    3. SETUP: Sobreviraje persistente en varias muestras seguidas con
       comportamiento consistente. Puede indicar que el coche está mal
       configurado (ARB trasero demasiado rígido, diferencial muy cerrado, etc.)
       Este tipo se detecta fuera de esta función, en el SessionAnalyzer,
       analizando la frecuencia de los otros dos tipos.

Umbrales calibrados con datos reales de ACR en gravel:
    - Los slip ratios en gravel son mucho más altos que en asfalto.
    - Un slip de 0.3 es perfectamente normal en una curva de rally.
    - Usamos 0.5 como umbral de detección (antes era 0.12, demasiado sensible).
"""

import numpy as np


# ── Umbrales calibrados para rally en gravel ──────────────────────────────────
# En asfalto (ACC/F1) el threshold típico es 0.05-0.12.
# En rally/gravel, el slip normal de las ruedas traseras puede ser 0.2-0.4
# por la pérdida de grip inherente a la superficie. Subimos el umbral.
OVERSTEER_SLIP_THRESHOLD = 0.50      # slip trasero para considerar sobreviraje real
INDUCED_THROTTLE_THRESHOLD = 0.70   # acelerador > 70% → sobreviraje probablemente inducido
INDUCED_STEERING_THRESHOLD = 0.20   # volante > 20% recorrido → en curva
MIN_SPEED_KMH = 20.0                # ignorar por debajo de 20 km/h (maniobras lentas)


def detect(wheel_speed_rl: float, wheel_speed_rr: float,
           vehicle_speed: float, steering_angle: float,
           throttle: float = 0.0) -> dict:
    """
    Detecta y clasifica el sobreviraje.

    Parámetros
    ----------
    wheel_speed_rl/rr : velocidad angular ruedas traseras (rad/s)
    vehicle_speed     : velocidad longitudinal del vehículo (m/s)
                        OJO: la memoria compartida de ACR da km/h — se espera m/s aquí.
    steering_angle    : ángulo de volante normalizado (-1.0 a 1.0)
    throttle          : posición del acelerador (0.0 a 1.0)

    Retorna
    -------
    dict con:
        'detected'       (bool)  — sobreviraje real detectado
        'oversteer_type' (str)   — 'induced' | 'driver_error' | 'none'
        'severity'       (float) — 0.0–1.0 (solo significativo si detected=True)
        'slip_ratio'     (float) — slip ratio trasero calculado
        'description'    (str)   — texto explicativo
    """
    speed_kmh = vehicle_speed * 3.6  # convertimos m/s → km/h para el filtro mínimo

    if speed_kmh < MIN_SPEED_KMH:
        return {
            "detected": False, "oversteer_type": "none",
            "severity": 0.0, "slip_ratio": 0.0,
            "description": "Velocidad insuficiente para análisis"
        }

    # El piloto tiene que estar girando para que tenga sentido hablar de sobreviraje
    if abs(steering_angle) < 0.08:
        return {
            "detected": False, "oversteer_type": "none",
            "severity": 0.0, "slip_ratio": 0.0,
            "description": "Volante recto — no aplica sobreviraje"
        }

    rear_avg = (wheel_speed_rl + wheel_speed_rr) / 2.0
    if vehicle_speed <= 0:
        return {
            "detected": False, "oversteer_type": "none",
            "severity": 0.0, "slip_ratio": 0.0,
            "description": "Sin velocidad de referencia"
        }

    slip_ratio = (rear_avg - vehicle_speed) / vehicle_speed

    if slip_ratio <= OVERSTEER_SLIP_THRESHOLD:
        return {
            "detected": False, "oversteer_type": "none",
            "severity": round(max(0.0, slip_ratio / OVERSTEER_SLIP_THRESHOLD), 4),
            "slip_ratio": round(slip_ratio, 4),
            "description": f"Slip trasero normal: {slip_ratio:.3f}"
        }

    # ── Sobreviraje detectado → clasificar el tipo ─────────────────────────
    severity = float(np.clip(
        (slip_ratio - OVERSTEER_SLIP_THRESHOLD) / OVERSTEER_SLIP_THRESHOLD,
        0.0, 1.0
    ))

    # Inducido: gas a fondo + volante girado → técnica deliberada de rally
    if throttle >= INDUCED_THROTTLE_THRESHOLD and abs(steering_angle) >= INDUCED_STEERING_THRESHOLD:
        oversteer_type = "induced"
        description = (
            f"Sobreviraje INDUCIDO — técnica de rally (gas:{throttle:.0%}, "
            f"slip:{slip_ratio:.2f}). No requiere cambio de setup."
        )
    else:
        # Sin gas o volante poco girado → pérdida de control no intencionada
        oversteer_type = "driver_error"
        description = (
            f"Sobreviraje NO inducido — posible error de piloto o setup "
            f"(gas:{throttle:.0%}, slip:{slip_ratio:.2f}, volante:{steering_angle:.2f})"
        )

    return {
        "detected": True,
        "oversteer_type": oversteer_type,
        "severity": round(severity, 4),
        "slip_ratio": round(slip_ratio, 4),
        "description": description,
    }

