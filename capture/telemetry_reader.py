"""
telemetry_reader.py
-------------------
Capa de Captura — Fase 3 del proyecto.

Responsabilidad: conectar con la memoria compartida de Windows expuesta por ACR
y devolver un TelemetryFrame con los datos en tiempo real.

TODO (Fase 3):
- Mapear la estructura exacta de la shared memory de ACR con ctypes.
- Implementar el bucle de lectura continua.
- Gestionar la reconexión si el juego no está corriendo.
"""

from models.telemetry_data import TelemetryFrame


class TelemetryReader:
    """Lee los datos de telemetría de ACR desde la memoria compartida de Windows."""

    SHARED_MEMORY_NAME = "Local\\ACRSharedMemory"  # nombre provisional

    def __init__(self):
        self._handle = None

    def connect(self) -> bool:
        """Abre la memoria compartida de ACR. Devuelve True si tiene éxito."""
        # TODO: implementar con pywin32 en Fase 3
        raise NotImplementedError("Conexión a memoria compartida pendiente (Fase 3)")

    def read_frame(self) -> TelemetryFrame:
        """Lee un frame de telemetría y lo devuelve como TelemetryFrame."""
        # TODO: implementar en Fase 3
        raise NotImplementedError("Lectura de frame pendiente (Fase 3)")

    def disconnect(self):
        """Cierra el handle de memoria compartida."""
        if self._handle:
            self._handle = None

