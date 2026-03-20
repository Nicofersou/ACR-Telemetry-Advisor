"""
test_analysis.py
----------------
Pruebas unitarias del motor de análisis.

Ejecutar con:  pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import understeer, oversteer, brake_lock


# ─── Tests de subviraje ──────────────────────────────────────────────────────

def test_understeer_not_detected_at_low_speed():
    result = understeer.detect(10, 10, 10, 10, vehicle_speed=0.5, steering_angle=0.5)
    assert result["detected"] is False


def test_understeer_detected():
    # Ruedas delanteras lentas respecto a traseras → subviraje
    result = understeer.detect(
        wheel_speed_fl=5.0, wheel_speed_fr=5.0,
        wheel_speed_rl=12.0, wheel_speed_rr=12.0,
        vehicle_speed=10.0, steering_angle=0.4
    )
    assert result["detected"] is True
    assert result["severity"] > 0.0


def test_understeer_not_detected_straight():
    # Sin ángulo de volante → no se considera subviraje
    result = understeer.detect(10, 10, 10, 10, vehicle_speed=20.0, steering_angle=0.0)
    assert result["detected"] is False


# ─── Tests de sobreviraje ─────────────────────────────────────────────────────

def test_oversteer_not_detected_at_low_speed():
    result = oversteer.detect(10, 10, vehicle_speed=0.3, steering_angle=0.3)
    assert result["detected"] is False


def test_oversteer_detected():
    # Ruedas traseras más rápidas que el vehículo → sobreviraje
    result = oversteer.detect(
        wheel_speed_rl=15.0, wheel_speed_rr=15.0,
        vehicle_speed=10.0, steering_angle=0.3
    )
    assert result["detected"] is True
    assert result["severity"] > 0.0


# ─── Tests de bloqueo de frenos ───────────────────────────────────────────────

def test_brake_lock_not_detected_without_braking():
    result = brake_lock.detect_brake_lock([10, 10, 10, 10], vehicle_speed=20.0, brake_input=0.0)
    assert result["detected"] is False


def test_brake_lock_detected():
    # Rueda FL casi parada mientras el coche va rápido y se frena fuerte
    result = brake_lock.detect_brake_lock([0.5, 10, 10, 10], vehicle_speed=20.0, brake_input=0.9)
    assert result["detected"] is True
    assert "FL" in result["locked_wheels"]


# ─── Tests de patinaje de tracción ───────────────────────────────────────────

def test_traction_slip_not_detected_without_throttle():
    result = brake_lock.detect_traction_slip(10.0, vehicle_speed=10.0, throttle_input=0.0)
    assert result["detected"] is False


def test_traction_slip_detected():
    result = brake_lock.detect_traction_slip(15.0, vehicle_speed=10.0, throttle_input=0.8)
    assert result["detected"] is True
    assert result["slip_ratio"] > 0.0

