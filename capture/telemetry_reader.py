"""
telemetry_reader.py
-------------------
Capa de Captura — Fase 3 / Fase 8 del proyecto.

Responsabilidad: conectar con la memoria compartida de Windows expuesta por ACR
y devolver TelemetryFrames con los datos en tiempo real.

Modos de operación:
    - mock=True  → usa datos simulados de capture/mock_data.py (desarrollo sin juego)
    - mock=False → conecta con acpmf_physics y acpmf_graphics de ACR via mmap

Lo que hemos confirmado con el explorador (Fase 8):
    ✅ acpmf_physics  → velocidad, inputs, velocidades de rueda, slip, G-forces
    ✅ acpmf_graphics → distanceTraveled (posición en la etapa)
    ⚠️  status/currentTime/surfaceGrip → no expuestos por ACR, los ignoramos
    ⚠️  tyreCoreTemperature → valor fijo (348.1), no fiable
"""

import mmap
import ctypes
import time
from typing import Optional, Iterator

from models.telemetry_data import TelemetryFrame
from capture.mock_data import generate_session_frames


# ─── Estructuras de Shared Memory (confirmadas con el explorador) ─────────────

class AcPhysics(ctypes.Structure):
    """
    Estructura de datos físicos de ACR (acpmf_physics).

    En Python, ctypes.Structure es la forma de leer bloques binarios de
    memoria con un layout fijo. Equivale a un struct en C o Java.
    Cada campo tiene un tipo (c_float, c_int) y un nombre.
    Los arrays se declaran como 'tipo * tamaño' (ej: c_float * 4).
    """
    _fields_ = [
        ("packetId",            ctypes.c_int),
        ("gas",                 ctypes.c_float),     # acelerador 0.0-1.0
        ("brake",               ctypes.c_float),     # freno 0.0-1.0
        ("fuel",                ctypes.c_float),
        ("gear",                ctypes.c_int),
        ("rpms",                ctypes.c_int),
        ("steerAngle",          ctypes.c_float),     # ángulo de volante normalizado
        ("speedKmh",            ctypes.c_float),     # velocidad en km/h
        ("velocity",            ctypes.c_float * 3),
        ("accG",                ctypes.c_float * 3), # G-forces: [lateral, ?, longitudinal]
        ("wheelSlip",           ctypes.c_float * 4), # slip ratio por rueda (FL,FR,RL,RR)
        ("wheelLoad",           ctypes.c_float * 4),
        ("wheelsPressure",      ctypes.c_float * 4), # presión neumáticos en PSI
        ("wheelAngularSpeed",   ctypes.c_float * 4), # velocidad angular ruedas (rad/s)
        ("tyreWear",            ctypes.c_float * 4),
        ("tyreDirtyLevel",      ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4), # ⚠️ fijo en ACR, no fiable
        ("camberRAD",           ctypes.c_float * 4),
        ("suspensionTravel",    ctypes.c_float * 4),
        ("drs",                 ctypes.c_float),
        ("tc",                  ctypes.c_float),
        ("heading",             ctypes.c_float),
        ("pitch",               ctypes.c_float),
        ("roll",                ctypes.c_float),
        ("cgHeight",            ctypes.c_float),
        ("carDamage",           ctypes.c_float * 5),
        ("numberOfTyresOut",    ctypes.c_int),
        ("pitLimiterOn",        ctypes.c_int),
        ("abs",                 ctypes.c_float),
        ("kersCharge",          ctypes.c_float),
        ("kersInput",           ctypes.c_float),
        ("autoShifterOn",       ctypes.c_int),
        ("rideHeight",          ctypes.c_float * 2),
        ("turboBoost",          ctypes.c_float),
        ("ballast",             ctypes.c_float),
        ("airDensity",          ctypes.c_float),
        ("airTemp",             ctypes.c_float),
        ("roadTemp",            ctypes.c_float),
        ("localAngularVel",     ctypes.c_float * 3),
        ("finalFF",             ctypes.c_float),
        ("performanceMeter",    ctypes.c_float),
        ("engineBrake",         ctypes.c_int),
        ("ersRecoveryLevel",    ctypes.c_int),
        ("ersPowerLevel",       ctypes.c_int),
        ("ersHeatCharging",     ctypes.c_int),
        ("ersIsCharging",       ctypes.c_int),
        ("kersCurrentKJ",       ctypes.c_float),
        ("drsAvailable",        ctypes.c_int),
        ("drsEnabled",          ctypes.c_int),
        ("brakeTemp",           ctypes.c_float * 4),
        ("clutch",              ctypes.c_float),
        ("tyreTempI",           ctypes.c_float * 4),
        ("tyreTempM",           ctypes.c_float * 4),
        ("tyreTempO",           ctypes.c_float * 4),
        ("isAIControlled",      ctypes.c_int),
        ("tyreContactPoint",    ctypes.c_float * 12),
        ("tyreContactNormal",   ctypes.c_float * 12),
        ("tyreContactHeading",  ctypes.c_float * 12),
        ("brakeBias",           ctypes.c_float),
        ("localVelocity",       ctypes.c_float * 3),
    ]


class AcGraphics(ctypes.Structure):
    """
    Estructura de datos gráficos de ACR (acpmf_graphics).
    Solo usamos distanceTraveled — el resto no está expuesto por ACR.
    """
    _fields_ = [
        ("packetId",              ctypes.c_int),
        ("status",                ctypes.c_int),
        ("session",               ctypes.c_int),
        ("currentTime",           ctypes.c_wchar * 15),
        ("lastTime",              ctypes.c_wchar * 15),
        ("bestTime",              ctypes.c_wchar * 15),
        ("split",                 ctypes.c_wchar * 15),
        ("completedLaps",         ctypes.c_int),
        ("position",              ctypes.c_int),
        ("iCurrentTime",          ctypes.c_int),
        ("iLastTime",             ctypes.c_int),
        ("iBestTime",             ctypes.c_int),
        ("sessionTimeLeft",       ctypes.c_float),
        ("distanceTraveled",      ctypes.c_float),   # ✅ distancia en la etapa (metros)
        ("isInPit",               ctypes.c_int),
        ("currentSectorIndex",    ctypes.c_int),
        ("lastSectorTime",        ctypes.c_int),
        ("numberOfLaps",          ctypes.c_int),
        ("tyreCompound",          ctypes.c_wchar * 33),
        ("replayTimeMultiplier",  ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
        ("carCoordinates",        ctypes.c_float * 3),
        ("penaltyTime",           ctypes.c_float),
        ("flag",                  ctypes.c_int),
        ("idealLineOn",           ctypes.c_int),
        ("isInPitLane",           ctypes.c_int),
        ("surfaceGrip",           ctypes.c_float),
        ("mandatoryPitDone",      ctypes.c_int),
        ("windSpeed",             ctypes.c_float),
        ("windDirection",         ctypes.c_float),
    ]


# ─── Lector principal ────────────────────────────────────────────────────────

class TelemetryReader:
    """
    Lee los datos de telemetría de ACR en tiempo real o en modo mock.

    Parámetros
    ----------
    mock : bool
        Si True, devuelve datos simulados (desarrollo sin juego abierto).
        Si False, conecta con la shared memory real de ACR.
    """

    PHYSICS_NAME  = "Local\\acpmf_physics"
    GRAPHICS_NAME = "Local\\acpmf_graphics"

    def __init__(self, mock: bool = True):
        self._mock = mock

        # Handles de shared memory (solo en modo real)
        self._physics_handle:  Optional[mmap.mmap] = None
        self._graphics_handle: Optional[mmap.mmap] = None

        # Tamaños de las estructuras en bytes
        self._physics_size  = ctypes.sizeof(AcPhysics)
        self._graphics_size = ctypes.sizeof(AcGraphics)

        # Modo mock
        self._mock_frames: list[TelemetryFrame] = []
        self._mock_index:  int = 0

        # Último packetId leído (para detectar frames nuevos)
        self._last_packet_id: int = -1

    # ─── Conexión ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Abre la fuente de datos.
        Retorna True si tuvo éxito, False en caso contrario.
        """
        if self._mock:
            self._mock_frames = generate_session_frames()
            self._mock_index  = 0
            print(f"[TelemetryReader] Modo mock — {len(self._mock_frames)} frames cargados.")
            return True

        return self._connect_real()

    def _connect_real(self) -> bool:
        """Abre los dos bloques de shared memory de ACR."""
        try:
            self._physics_handle = mmap.mmap(
                -1, self._physics_size,
                self.PHYSICS_NAME,
                access=mmap.ACCESS_READ
            )
        except Exception as e:
            print(f"[TelemetryReader] No se pudo abrir acpmf_physics: {e}")
            print("[TelemetryReader] ¿Está ACR abierto y en una etapa?")
            return False

        try:
            self._graphics_handle = mmap.mmap(
                -1, self._graphics_size,
                self.GRAPHICS_NAME,
                access=mmap.ACCESS_READ
            )
        except Exception as e:
            # Los gráficos son opcionales — podemos funcionar sin distancia
            print(f"[TelemetryReader] acpmf_graphics no disponible: {e} (continuando sin distancia)")

        print("[TelemetryReader] Conectado a ACR shared memory.")
        return True

    # ─── Lectura de frame ──────────────────────────────────────────────────────

    def read_frame(self) -> Optional[TelemetryFrame]:
        """
        Lee y devuelve el siguiente TelemetryFrame.
        Retorna None si no hay datos nuevos o la sesión mock terminó.
        """
        if self._mock:
            return self._read_mock_frame()
        return self._read_real_frame()

    def _read_mock_frame(self) -> Optional[TelemetryFrame]:
        """Devuelve el siguiente frame simulado."""
        if self._mock_index >= len(self._mock_frames):
            return None
        frame = self._mock_frames[self._mock_index]
        self._mock_index += 1
        return frame

    def _read_real_frame(self) -> Optional[TelemetryFrame]:
        """
        Lee un frame desde la shared memory real de ACR y lo convierte
        a un TelemetryFrame normalizado.

        Conversiones aplicadas:
        - speedKmh / 3.6  → m/s  (vehicle_speed)
        - wheelAngularSpeed ya está en rad/s → lo usamos directamente
        - accG[0] → lateral_g,  accG[2] → longitudinal_g
        - steerAngle ya está normalizado (-1 a 1)
        """
        if self._physics_handle is None:
            return None

        try:
            # Leer physics
            self._physics_handle.seek(0)
            raw_physics = self._physics_handle.read(self._physics_size)
            physics = AcPhysics.from_buffer_copy(raw_physics)

            # Evitar procesar el mismo frame dos veces (ACR actualiza a ~60fps)
            if physics.packetId == self._last_packet_id:
                return None
            self._last_packet_id = physics.packetId

            # Leer distancia desde graphics (opcional)
            stage_distance = 0.0
            if self._graphics_handle:
                self._graphics_handle.seek(0)
                raw_graphics = self._graphics_handle.read(self._graphics_size)
                graphics = AcGraphics.from_buffer_copy(raw_graphics)
                stage_distance = graphics.distanceTraveled

            # Construir el TelemetryFrame normalizado
            return TelemetryFrame(
                timestamp       = time.time(),
                # Inputs del piloto
                throttle        = float(physics.gas),
                brake           = float(physics.brake),
                steering_angle  = float(physics.steerAngle),
                # Velocidad del vehículo (km/h → m/s)
                vehicle_speed   = float(physics.speedKmh) / 3.6,
                # Velocidades angulares de ruedas (FL, FR, RL, RR) en rad/s
                wheel_speed_fl  = float(physics.wheelAngularSpeed[0]),
                wheel_speed_fr  = float(physics.wheelAngularSpeed[1]),
                wheel_speed_rl  = float(physics.wheelAngularSpeed[2]),
                wheel_speed_rr  = float(physics.wheelAngularSpeed[3]),
                # G-forces (confirmados con el explorador)
                lateral_g       = float(physics.accG[0]),
                longitudinal_g  = float(physics.accG[2]),
                # Posición en la etapa
                stage_distance  = stage_distance,
                # Superficie: no disponible en ACR todavía
                surface         = None,
            )

        except Exception as e:
            print(f"[TelemetryReader] Error leyendo frame: {e}")
            return None

    # ─── Iterador de sesión ────────────────────────────────────────────────────

    def iter_session(self, fps: int = 60) -> Iterator[TelemetryFrame]:
        """
        Generador que produce frames a la cadencia indicada.

        En modo real lee tan rápido como ACR actualiza la shared memory
        y filtra frames duplicados por packetId. En modo mock simula el
        tiempo real con sleep.

        Uso:
            for frame in reader.iter_session():
                procesar(frame)
        """
        delay = 1.0 / fps

        while True:
            frame = self.read_frame()
            if frame is None:
                if self._mock:
                    break          # sesión mock terminada
                time.sleep(0.001)  # en modo real: esperar frame nuevo
                continue
            yield frame
            if self._mock:
                time.sleep(delay)

    # ─── Desconexión ──────────────────────────────────────────────────────────

    def disconnect(self):
        """Cierra los handles de shared memory."""
        for handle in (self._physics_handle, self._graphics_handle):
            if handle:
                try:
                    handle.close()
                except Exception:
                    pass
        self._physics_handle  = None
        self._graphics_handle = None
        self._mock_frames = []
        self._mock_index  = 0
        print("[TelemetryReader] Desconectado.")
