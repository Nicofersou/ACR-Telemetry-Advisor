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
from analysis.session_analyzer import SessionAnalyzer
from capture.mock_data import generate_session_frames


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


# ─── Tests del orquestador SessionAnalyzer ────────────────────────────────────

def test_session_analyzer_returns_report():
    """El analizador debe devolver un SessionReport sin errores."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    assert report is not None


def test_session_analyzer_counts_frames():
    """El total de frames del informe debe coincidir con los frames enviados."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    assert report.total_frames == len(frames)


def test_session_analyzer_detects_incidents():
    """Con los datos mock debe haber al menos un incidente detectado."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    assert report.total_incidents > 0


def test_session_analyzer_detects_understeer():
    """Los datos mock incluyen un escenario de subviraje — debe detectarse."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    understeer_incidents = [i for i in report.incidents if i.incident_type == "understeer"]
    assert len(understeer_incidents) > 0


def test_session_analyzer_detects_oversteer():
    """Los datos mock incluyen un escenario de sobreviraje — debe detectarse."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    oversteer_incidents = [i for i in report.incidents if i.incident_type == "oversteer"]
    assert len(oversteer_incidents) > 0


def test_session_analyzer_detects_brake_lock():
    """Los datos mock incluyen frenada con bloqueo — debe detectarse."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    brake_incidents = [i for i in report.incidents if i.incident_type == "brake_lock"]
    assert len(brake_incidents) > 0


def test_session_analyzer_detects_traction_slip():
    """Los datos mock incluyen patinaje de tracción al arrancar — debe detectarse."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    slip_incidents = [i for i in report.incidents if i.incident_type == "traction_slip"]
    assert len(slip_incidents) > 0


def test_session_analyzer_severities_in_range():
    """Todas las severidades medias deben estar entre 0.0 y 1.0."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    assert 0.0 <= report.avg_understeer_severity <= 1.0
    assert 0.0 <= report.avg_oversteer_severity <= 1.0
    assert 0.0 <= report.avg_brake_lock_severity <= 1.0
    assert 0.0 <= report.avg_traction_slip_severity <= 1.0


def test_session_analyzer_surface_is_gravel():
    """Los datos mock usan superficie gravel — debe aparecer en el informe."""
    frames = generate_session_frames()
    analyzer = SessionAnalyzer()
    report = analyzer.analyze(frames)
    assert report.surface == "gravel"


def test_session_analyzer_empty_frames():
    """Con una lista vacía no debe lanzar excepción y devuelve 0 incidentes."""
    analyzer = SessionAnalyzer()
    report = analyzer.analyze([])
    assert report.total_frames == 0
    assert report.total_incidents == 0



