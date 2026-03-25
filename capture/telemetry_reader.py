"""
telemetry_reader.py
-------------------
Capa de Captura — Fase 3 del proyecto.

Responsabilidad: conectar con la memoria compartida de Windows expuesta por ACR
y devolver un TelemetryFrame con los datos en tiempo real.

Modos de operación:
    - mock=True  → usa datos simulados de capture/mock_data.py (desarrollo sin juego)
    - mock=False → conecta con la shared memory real de ACR via mmap (producción)

TODO (cuando ACR documente su shared memory):
    - Mapear la estructura exacta con ctypes.Structure.
    - Implementar el bucle de lectura continua con threading.
    - Gestionar la reconexión si el juego no está corriendo.
"""

import mmap
import time
from typing import Optional

from models.telemetry_data import TelemetryFrame
from capture.mock_data import generate_session_frames


class TelemetryReader:
    """
    Lee los datos de telemetría de ACR.

    Parámetros
    ----------
    mock : bool
        Si True, devuelve datos simulados en lugar de conectar con ACR.
        Útil para desarrollo y pruebas sin el juego abierto.
    """

    SHARED_MEMORY_NAME = "Local\\ACRSharedMemory"  # nombre de la shared memory de ACR

    def __init__(self, mock: bool = True):
        self._mock = mock
        self._handle: Optional[mmap.mmap] = None   # handle a la shared memory real

        # En modo mock: cargamos todos los frames simulados y los recorremos uno a uno
        self._mock_frames: list[TelemetryFrame] = []
        self._mock_index: int = 0

    # ─── Conexión ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Abre la fuente de datos (shared memory real o mock).

        Retorna True si la conexión tuvo éxito, False en caso contrario.
        En modo mock siempre retorna True.
        """
        if self._mock:
            self._mock_frames = generate_session_frames()
            self._mock_index = 0
            print(f"[TelemetryReader] Modo mock activado — {len(self._mock_frames)} frames cargados.")
            return True

        # Modo real: abre la shared memory de Windows
        try:
            self._handle = mmap.mmap(
                -1,                          # -1 = crear nueva región (no asociada a fichero)
                4096,                        # tamaño provisional en bytes
                self.SHARED_MEMORY_NAME,     # nombre del objeto de memoria compartida
                access=mmap.ACCESS_READ      # solo lectura
            )
            print("[TelemetryReader] Conectado a la shared memory de ACR.")
            return True

        except Exception as e:
            print(f"[TelemetryReader] Error al conectar con ACR: {e}")
            print("[TelemetryReader] ¿Está ACR abierto y corriendo?")
            return False

    # ─── Lectura de frame ─────────────────────────────────────────────────────

    def read_frame(self) -> Optional[TelemetryFrame]:
        """
        Lee y devuelve el siguiente TelemetryFrame.

        - En modo mock: devuelve los frames simulados en orden. Cuando se
          agotan, devuelve None para indicar que la sesión ha terminado.
        - En modo real: lee la shared memory de ACR y construye el frame.
          (Pendiente de implementar cuando ACR publique su estructura.)

        Retorna None si no hay datos disponibles o la sesión terminó.
        """
        if self._mock:
            return self._read_mock_frame()

        return self._read_real_frame()

    def _read_mock_frame(self) -> Optional[TelemetryFrame]:
        """Devuelve el siguiente frame simulado de la lista."""
        if self._mock_index >= len(self._mock_frames):
            return None   # sesión simulada terminada

        frame = self._mock_frames[self._mock_index]
        self._mock_index += 1
        return frame

    def _read_real_frame(self) -> Optional[TelemetryFrame]:
        """
        Lee un frame desde la shared memory real de ACR.

        TODO (Fase 3 — cuando ACR publique la estructura de su shared memory):
            1. Leer los bytes desde self._handle con self._handle.read(...)
            2. Parsear los bytes con ctypes.Structure para extraer cada campo.
            3. Mapear los campos al TelemetryFrame y devolverlo.
        """
        if self._handle is None:
            return None

        # Placeholder hasta tener la estructura real de ACR
        raise NotImplementedError(
            "Lectura real pendiente — ACR shared memory no documentada aún.\n"
            "Usa mock=True para desarrollo."
        )

    # ─── Iterador de sesión completa ─────────────────────────────────────────

    def iter_session(self, fps: int = 60):
        """
        Generador que produce frames a la cadencia indicada.

        Uso:
            for frame in reader.iter_session():
                procesar(frame)

        Parámetros
        ----------
        fps : int
            Frames por segundo. En modo mock simula el tiempo real con sleep.
            En modo real se lee tan rápido como la shared memory actualice.
        """
        delay = 1.0 / fps

        while True:
            frame = self.read_frame()
            if frame is None:
                break
            yield frame
            if self._mock:
                time.sleep(delay)   # simula cadencia real en modo mock

    # ─── Desconexión ─────────────────────────────────────────────────────────

    def disconnect(self):
        """Cierra el handle de shared memory y libera recursos."""
        if self._handle:
            self._handle.close()
            self._handle = None
            print("[TelemetryReader] Desconectado.")

        self._mock_frames = []
        self._mock_index = 0

