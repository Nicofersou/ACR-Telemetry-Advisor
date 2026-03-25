"""
mock_data.py
------------
Generador de datos de telemetría simulados.

Responsabilidad: producir TelemetryFrames con datos realistas para poder
desarrollar y probar el motor de análisis, la UI y el LLM sin necesidad
de tener ACR abierto.

Los datos simulan una secuencia de conducción con:
    - Aceleración desde parado
    - Curva con subviraje leve
    - Frenada con bloqueo puntual
    - Curva con sobreviraje
    - Recta final
"""

import time
from models.telemetry_data import TelemetryFrame


# ─── Escenarios disponibles ───────────────────────────────────────────────────

# Cada escenario es un diccionario con los valores base de un tramo de conducción.
# 'duration' indica cuántos frames dura el escenario (a ~60 fps → 60 frames = 1 segundo).

SCENARIOS = [
    {
        "name": "Aceleración desde parado",
        "duration": 120,
        "vehicle_speed": 0.0,        # sube progresivamente
        "wheel_speed_base": 0.0,     # ruedas arrancan desde 0
        "steering_angle": 0.0,
        "throttle": 0.85,
        "brake": 0.0,
        "lateral_g": 0.0,
        "longitudinal_g": 0.4,
        "traction_slip": True,       # patinaje al salir
    },
    {
        "name": "Recta a velocidad",
        "duration": 180,
        "vehicle_speed": 28.0,       # ~100 km/h
        "wheel_speed_base": 28.0,
        "steering_angle": 0.0,
        "throttle": 0.9,
        "brake": 0.0,
        "lateral_g": 0.0,
        "longitudinal_g": 0.1,
        "traction_slip": False,
    },
    {
        "name": "Curva con subviraje",
        "duration": 150,
        "vehicle_speed": 22.0,
        "wheel_speed_base": 22.0,
        "steering_angle": 0.45,
        "throttle": 0.3,
        "brake": 0.0,
        "lateral_g": 0.6,
        "longitudinal_g": -0.1,
        "traction_slip": False,
        "understeer": True,          # ruedas delanteras más lentas
    },
    {
        "name": "Frenada con bloqueo",
        "duration": 90,
        "vehicle_speed": 22.0,       # decae bruscamente
        "wheel_speed_base": 22.0,
        "steering_angle": 0.0,
        "throttle": 0.0,
        "brake": 0.95,
        "lateral_g": 0.0,
        "longitudinal_g": -0.85,
        "traction_slip": False,
        "brake_lock": True,          # rueda delantera izquierda bloquea
    },
    {
        "name": "Curva con sobreviraje",
        "duration": 120,
        "vehicle_speed": 18.0,
        "wheel_speed_base": 18.0,
        "steering_angle": -0.35,
        "throttle": 0.6,
        "brake": 0.0,
        "lateral_g": -0.55,
        "longitudinal_g": 0.05,
        "traction_slip": False,
        "oversteer": True,           # ruedas traseras más rápidas
    },
    {
        "name": "Recta final",
        "duration": 200,
        "vehicle_speed": 30.0,
        "wheel_speed_base": 30.0,
        "steering_angle": 0.0,
        "throttle": 1.0,
        "brake": 0.0,
        "lateral_g": 0.0,
        "longitudinal_g": 0.2,
        "traction_slip": False,
    },
]


# ─── Generador de frames ──────────────────────────────────────────────────────

def generate_session_frames() -> list[TelemetryFrame]:
    """
    Genera la lista completa de TelemetryFrames para una sesión simulada.

    Recorre todos los escenarios de SCENARIOS y produce un frame por cada
    tick, añadiendo variación aleatoria pequeña para simular ruido de sensor.

    Retorna
    -------
    list[TelemetryFrame] — todos los frames de la sesión en orden temporal
    """
    import random

    frames = []
    stage_distance = 0.0
    timestamp = time.time()

    for scenario in SCENARIOS:
        duration = scenario["duration"]
        base_speed = scenario["vehicle_speed"]
        base_wheels = scenario["wheel_speed_base"]

        for tick in range(duration):
            # Progresión normalizada dentro del escenario (0.0 → 1.0)
            progress = tick / duration

            # Velocidad del vehículo — puede subir o bajar según el escenario
            if scenario["name"] == "Aceleración desde parado":
                speed = base_speed + progress * 25.0
            elif scenario["name"] == "Frenada con bloqueo":
                speed = max(base_speed * (1.0 - progress * 0.8), 3.0)
            else:
                speed = base_speed + random.uniform(-0.5, 0.5)

            # Ruido de sensor realista (±1%)
            noise = lambda: random.uniform(-0.01, 0.01)

            # Velocidades angulares base de las 4 ruedas
            wfl = speed * (1 + noise())
            wfr = speed * (1 + noise())
            wrl = speed * (1 + noise())
            wrr = speed * (1 + noise())

            # Aplicar efectos de cada escenario
            if scenario.get("understeer"):
                # Delanteras más lentas que traseras
                wfl *= 0.78
                wfr *= 0.78

            if scenario.get("oversteer"):
                # Traseras más rápidas que el vehículo
                wrl *= 1.18
                wrr *= 1.18

            if scenario.get("brake_lock"):
                # Rueda delantera izquierda cae a casi 0
                wfl *= max(0.05, 1.0 - progress * 1.5)

            if scenario.get("traction_slip"):
                # Ruedas motrices patinan en la salida
                spin = (1.0 - progress) * 0.4
                wrl *= (1 + spin)
                wrr *= (1 + spin)

            # Distancia recorrida acumulada (integración simple: d = v * dt)
            dt = 1.0 / 60.0  # asumimos 60 fps
            stage_distance += speed * dt
            timestamp += dt

            frames.append(TelemetryFrame(
                timestamp=timestamp,
                wheel_speed_fl=round(wfl, 3),
                wheel_speed_fr=round(wfr, 3),
                wheel_speed_rl=round(wrl, 3),
                wheel_speed_rr=round(wrr, 3),
                vehicle_speed=round(speed, 3),
                lateral_g=round(scenario["lateral_g"] + random.uniform(-0.02, 0.02), 3),
                longitudinal_g=round(scenario["longitudinal_g"] + random.uniform(-0.02, 0.02), 3),
                steering_angle=round(scenario["steering_angle"] + random.uniform(-0.01, 0.01), 3),
                throttle=round(min(1.0, max(0.0, scenario["throttle"] + random.uniform(-0.02, 0.02))), 3),
                brake=round(min(1.0, max(0.0, scenario["brake"] + random.uniform(-0.02, 0.02))), 3),
                stage_distance=round(stage_distance, 2),
                surface="gravel",
            ))

    return frames

