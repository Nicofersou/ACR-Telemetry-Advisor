"""
acr_explorer.py
---------------
Herramienta de exploración de la Shared Memory de ACR.

Responsabilidad: conectarse a la memoria compartida de ACR mientras el juego
está corriendo y volcar su contenido para entender qué datos expone y cómo
están estructurados.

Uso:
    1. Abre Assetto Corsa Rally y entra en una etapa.
    2. Ejecuta este script desde la terminal:
           .venv\\Scripts\\python.exe capture\\acr_explorer.py

ACR hereda la arquitectura de shared memory de Assetto Corsa original.
Los nombres más probables son los del SDK de AC:
    - "Local\\acpmf_physics"   → datos físicos (velocidades, g-forces, inputs)
    - "Local\\acpmf_graphics"  → datos gráficos (posición, estado de sesión)
    - "Local\\acpmf_static"    → datos estáticos (nombre del coche, pista, etc.)
"""

import mmap
import struct
import ctypes
import ctypes.wintypes
import time
import sys


# ─── Nombres de shared memory conocidos de AC/ACR ─────────────────────────────

KNOWN_NAMES = [
    "Local\\acpmf_physics",
    "Local\\acpmf_graphics",
    "Local\\acpmf_static",
    "Local\\ACRSharedMemory",
    "Local\\AcrPhysics",
    "Local\\AcrGraphics",
    "Local\\AcrStatic",
]


# ─── Estructura de Physics de Assetto Corsa (SDK oficial) ─────────────────────
# ACR probablemente hereda esta estructura o una versión extendida.

class AcPhysics(ctypes.Structure):
    """
    Estructura de datos físicos de Assetto Corsa (acpmf_physics).
    Basada en el SDK oficial de AC. ACR muy probablemente la comparte.
    """
    _fields_ = [
        ("packetId",          ctypes.c_int),
        ("gas",               ctypes.c_float),      # acelerador 0.0-1.0
        ("brake",             ctypes.c_float),      # freno 0.0-1.0
        ("fuel",              ctypes.c_float),
        ("gear",              ctypes.c_int),
        ("rpms",              ctypes.c_int),
        ("steerAngle",        ctypes.c_float),      # ángulo de volante
        ("speedKmh",          ctypes.c_float),      # velocidad en km/h
        ("velocity",          ctypes.c_float * 3),  # velocidad vectorial XYZ
        ("accG",              ctypes.c_float * 3),  # aceleraciones G (X, Y, Z)
        ("wheelSlip",         ctypes.c_float * 4),  # slip de cada rueda
        ("wheelLoad",         ctypes.c_float * 4),
        ("wheelsPressure",    ctypes.c_float * 4),  # presiones de neumáticos
        ("wheelAngularSpeed", ctypes.c_float * 4),  # velocidad angular ruedas
        ("tyreWear",          ctypes.c_float * 4),
        ("tyreDirtyLevel",    ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD",         ctypes.c_float * 4),
        ("suspensionTravel",  ctypes.c_float * 4),
        ("drs",               ctypes.c_float),
        ("tc",                ctypes.c_float),
        ("heading",           ctypes.c_float),
        ("pitch",             ctypes.c_float),
        ("roll",              ctypes.c_float),
        ("cgHeight",          ctypes.c_float),
        ("carDamage",         ctypes.c_float * 5),
        ("numberOfTyresOut",  ctypes.c_int),
        ("pitLimiterOn",      ctypes.c_int),
        ("abs",               ctypes.c_float),
        ("kersCharge",        ctypes.c_float),
        ("kersInput",         ctypes.c_float),
        ("autoShifterOn",     ctypes.c_int),
        ("rideHeight",        ctypes.c_float * 2),
        ("turboBoost",        ctypes.c_float),
        ("ballast",           ctypes.c_float),
        ("airDensity",        ctypes.c_float),
        ("airTemp",           ctypes.c_float),
        ("roadTemp",          ctypes.c_float),
        ("localAngularVel",   ctypes.c_float * 3),  # velocidad angular local
        ("finalFF",           ctypes.c_float),
        ("performanceMeter",  ctypes.c_float),
        ("engineBrake",       ctypes.c_int),
        ("ersRecoveryLevel",  ctypes.c_int),
        ("ersPowerLevel",     ctypes.c_int),
        ("ersHeatCharging",   ctypes.c_int),
        ("ersIsCharging",     ctypes.c_int),
        ("kersCurrentKJ",     ctypes.c_float),
        ("drsAvailable",      ctypes.c_int),
        ("drsEnabled",        ctypes.c_int),
        ("brakeTemp",         ctypes.c_float * 4),
        ("clutch",            ctypes.c_float),
        ("tyreTempI",         ctypes.c_float * 4),
        ("tyreTempM",         ctypes.c_float * 4),
        ("tyreTempO",         ctypes.c_float * 4),
        ("isAIControlled",    ctypes.c_int),
        ("tyreContactPoint",  ctypes.c_float * 12),
        ("tyreContactNormal", ctypes.c_float * 12),
        ("tyreContactHeading", ctypes.c_float * 12),
        ("brakeBias",         ctypes.c_float),
        ("localVelocity",     ctypes.c_float * 3),
    ]


class AcGraphics(ctypes.Structure):
    """Estructura de datos gráficos de Assetto Corsa (acpmf_graphics)."""
    _fields_ = [
        ("packetId",           ctypes.c_int),
        ("status",             ctypes.c_int),       # 0=OFF, 1=REPLAY, 2=LIVE, 3=PAUSE
        ("session",            ctypes.c_int),
        ("currentTime",        ctypes.c_wchar * 15),
        ("lastTime",           ctypes.c_wchar * 15),
        ("bestTime",           ctypes.c_wchar * 15),
        ("split",              ctypes.c_wchar * 15),
        ("completedLaps",      ctypes.c_int),
        ("position",           ctypes.c_int),
        ("iCurrentTime",       ctypes.c_int),       # tiempo actual en ms
        ("iLastTime",          ctypes.c_int),
        ("iBestTime",          ctypes.c_int),
        ("sessionTimeLeft",    ctypes.c_float),
        ("distanceTraveled",   ctypes.c_float),     # distancia recorrida en la etapa
        ("isInPit",            ctypes.c_int),
        ("currentSectorIndex", ctypes.c_int),
        ("lastSectorTime",     ctypes.c_int),
        ("numberOfLaps",       ctypes.c_int),
        ("tyreCompound",       ctypes.c_wchar * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
        ("carCoordinates",     ctypes.c_float * 3),
        ("penaltyTime",        ctypes.c_float),
        ("flag",               ctypes.c_int),
        ("idealLineOn",        ctypes.c_int),
        ("isInPitLane",        ctypes.c_int),
        ("surfaceGrip",        ctypes.c_float),     # grip de la superficie
        ("mandatoryPitDone",   ctypes.c_int),
        ("windSpeed",          ctypes.c_float),
        ("windDirection",      ctypes.c_float),
    ]


class AcStatic(ctypes.Structure):
    """Estructura de datos estáticos de Assetto Corsa (acpmf_static)."""
    _fields_ = [
        ("smVersion",          ctypes.c_wchar * 15),
        ("acVersion",          ctypes.c_wchar * 15),
        ("numberOfSessions",   ctypes.c_int),
        ("numCars",            ctypes.c_int),
        ("carModel",           ctypes.c_wchar * 33),   # nombre del coche
        ("track",              ctypes.c_wchar * 33),   # nombre de la pista
        ("playerName",         ctypes.c_wchar * 33),
        ("playerSurname",      ctypes.c_wchar * 33),
        ("playerNick",         ctypes.c_wchar * 33),
        ("sectorCount",        ctypes.c_int),
        ("maxTorque",          ctypes.c_float),
        ("maxPower",           ctypes.c_float),
        ("maxRpm",             ctypes.c_int),
        ("maxFuel",            ctypes.c_float),
        ("suspensionMaxTravel", ctypes.c_float * 4),
        ("tyreRadius",         ctypes.c_float * 4),
        ("maxTurboBoost",      ctypes.c_float),
        ("airTemp",            ctypes.c_float),
        ("roadTemp",           ctypes.c_float),
        ("penaltiesEnabled",   ctypes.c_int),
        ("aidFuelRate",        ctypes.c_float),
        ("aidTireRate",        ctypes.c_float),
        ("aidMechanicalDamage", ctypes.c_float),
        ("aidAllowTyreBlankets", ctypes.c_int),
        ("aidStability",       ctypes.c_float),
        ("aidAutoClutch",      ctypes.c_int),
        ("aidAutoBlip",        ctypes.c_int),
        ("hasDRS",             ctypes.c_int),
        ("hasERS",             ctypes.c_int),
        ("hasKERS",            ctypes.c_int),
        ("kersMaxJ",           ctypes.c_float),
        ("engineBrakeSettingsCount", ctypes.c_int),
        ("ersPowerControllerCount",  ctypes.c_int),
        ("trackSPlineLength",  ctypes.c_float),
        ("trackConfiguration", ctypes.c_wchar * 33),
        ("ersMaxJ",            ctypes.c_float),
        ("isTimedRace",        ctypes.c_int),
        ("hasExtraLap",        ctypes.c_int),
        ("tyreAllowedCompounds", ctypes.c_wchar * 33),
        ("hasMandatoryPit",    ctypes.c_int),
        ("fuelXLap",           ctypes.c_float),
        ("safetyCarStatus",    ctypes.c_int),
        ("numPitStops",        ctypes.c_int),
    ]


# ─── Funciones de exploración ─────────────────────────────────────────────────

def try_open_shared_memory(name: str, size: int = 4096) -> mmap.mmap | None:
    """
    Intenta abrir un bloque de shared memory por nombre.
    Retorna el objeto mmap si tiene éxito, None si no existe.
    """
    try:
        handle = mmap.mmap(-1, size, name, access=mmap.ACCESS_READ)
        # Comprobamos que no está vacía (todos ceros = no hay datos)
        handle.seek(0)
        data = handle.read(16)
        if all(b == 0 for b in data):
            handle.close()
            return None
        handle.seek(0)
        return handle
    except Exception:
        return None


def scan_all_known_names() -> dict[str, mmap.mmap]:
    """Escanea todos los nombres conocidos y retorna los que están activos."""
    found = {}
    for name in KNOWN_NAMES:
        handle = try_open_shared_memory(name)
        if handle:
            found[name] = handle
            print(f"  ✅  Encontrado: {name}")
        else:
            print(f"  ❌  No disponible: {name}")
    return found


def read_physics(handle: mmap.mmap) -> None:
    """Lee e imprime los datos de física más relevantes."""
    handle.seek(0)
    raw = handle.read(ctypes.sizeof(AcPhysics))
    physics = AcPhysics.from_buffer_copy(raw)

    print("\n=== FÍSICA (acpmf_physics) ===")
    print(f"  Velocidad         : {physics.speedKmh:.1f} km/h")
    print(f"  Acelerador        : {physics.gas:.2f}")
    print(f"  Freno             : {physics.brake:.2f}")
    print(f"  Ángulo volante    : {physics.steerAngle:.3f}")
    print(f"  Marcha            : {physics.gear}")
    print(f"  RPM               : {physics.rpms}")
    print(f"  G lateral         : {physics.accG[0]:.3f}")
    print(f"  G longitudinal    : {physics.accG[2]:.3f}")
    print(f"  Vel. angular ruedas (FL,FR,RL,RR): "
          f"{physics.wheelAngularSpeed[0]:.2f}, {physics.wheelAngularSpeed[1]:.2f}, "
          f"{physics.wheelAngularSpeed[2]:.2f}, {physics.wheelAngularSpeed[3]:.2f}")
    print(f"  Slip ruedas       : "
          f"{physics.wheelSlip[0]:.3f}, {physics.wheelSlip[1]:.3f}, "
          f"{physics.wheelSlip[2]:.3f}, {physics.wheelSlip[3]:.3f}")
    print(f"  Presiones         : "
          f"{physics.wheelsPressure[0]:.1f}, {physics.wheelsPressure[1]:.1f}, "
          f"{physics.wheelsPressure[2]:.1f}, {physics.wheelsPressure[3]:.1f} PSI")
    print(f"  Temp. núcleo neumáticos: "
          f"{physics.tyreCoreTemperature[0]:.1f}, {physics.tyreCoreTemperature[1]:.1f}, "
          f"{physics.tyreCoreTemperature[2]:.1f}, {physics.tyreCoreTemperature[3]:.1f} °C")


def read_graphics(handle: mmap.mmap) -> None:
    """Lee e imprime los datos gráficos más relevantes."""
    handle.seek(0)
    raw = handle.read(ctypes.sizeof(AcGraphics))
    graphics = AcGraphics.from_buffer_copy(raw)

    status_map = {0: "APAGADO", 1: "REPLAY", 2: "EN PISTA", 3: "PAUSA"}
    print("\n=== GRÁFICOS (acpmf_graphics) ===")
    print(f"  Estado sesión     : {status_map.get(graphics.status, graphics.status)}")
    print(f"  Tiempo actual     : {graphics.currentTime}")
    print(f"  Mejor tiempo      : {graphics.bestTime}")
    print(f"  Vueltas           : {graphics.completedLaps}")
    print(f"  Distancia recorrida: {graphics.distanceTraveled:.1f} m")
    print(f"  Grip superficie   : {graphics.surfaceGrip:.3f}")
    print(f"  Compuesto neumático: {graphics.tyreCompound}")


def read_static(handle: mmap.mmap) -> None:
    """Lee e imprime los datos estáticos."""
    handle.seek(0)
    raw = handle.read(ctypes.sizeof(AcStatic))
    static = AcStatic.from_buffer_copy(raw)

    print("\n=== ESTÁTICOS (acpmf_static) ===")
    print(f"  Coche             : {static.carModel}")
    print(f"  Pista             : {static.track}")
    print(f"  Piloto            : {static.playerName} {static.playerSurname}")
    print(f"  Longitud de pista : {static.trackSPlineLength:.1f} m")
    print(f"  Máx. RPM          : {static.maxRpm}")


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  ACR Telemetry Explorer — Escáner de Shared Memory")
    print("=" * 55)
    print("\n🔍  Buscando bloques de shared memory de ACR...\n")

    found = scan_all_known_names()

    if not found:
        print("\n⚠️  No se encontró ningún bloque de shared memory.")
        print("   Asegúrate de que ACR está abierto y en una etapa activa.")
        return

    print(f"\n✅  {len(found)} bloque(s) encontrado(s). Iniciando lectura continua...")
    print("   Pulsa Ctrl+C para detener.\n")

    try:
        while True:
            for name, handle in found.items():
                handle.seek(0)
                if "physics" in name.lower() or "acpmf_physics" in name:
                    read_physics(handle)
                elif "graphics" in name.lower() or "acpmf_graphics" in name:
                    read_graphics(handle)
                elif "static" in name.lower() or "acpmf_static" in name:
                    read_static(handle)
                else:
                    # Bloque desconocido: volcamos los primeros bytes en hex
                    handle.seek(0)
                    raw = handle.read(64)
                    print(f"\n=== {name} (raw hex) ===")
                    print("  " + raw.hex(" "))

            print("\n" + "-" * 55)
            time.sleep(1.0)   # actualiza cada segundo

    except KeyboardInterrupt:
        print("\n\nExplorador detenido.")

    finally:
        for h in found.values():
            h.close()


if __name__ == "__main__":
    main()

