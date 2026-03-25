"""
context_loader.py
-----------------
Cargador de contexto para el sistema de recomendaciones — Fase 7.

Responsabilidad: leer los ficheros JSON de coches y tramos de la carpeta
data/ y transformarlos en texto estructurado listo para inyectar en el
prompt de Ollama.

Flujo:
    car_id + stage_id + setup_actual
        → ContextLoader.build_context()
        → str (contexto rico para el LLM)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


# Ruta base de los datos — relativa al directorio raíz del proyecto
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


# ─── Modelo de contexto de sesión ─────────────────────────────────────────────

@dataclass
class SessionContext:
    """
    Agrupa toda la información contextual de una sesión.

    Se construye antes del análisis y se pasa al SetupAdvisor junto
    con el SessionReport para enriquecer el prompt.

    En Python, @dataclass genera automáticamente __init__, __repr__, etc.
    En Java equivaldría a un POJO con Lombok @Data.
    """
    car_id: str                        # ej: "Hyundaii20NRally2"
    stage_id: str                      # ej: "Munster"
    current_setup: Optional[dict] = field(default_factory=dict)
    # Si current_setup está vacío, se usará el setup_base del JSON del coche


# ─── Clase principal ──────────────────────────────────────────────────────────

class ContextLoader:
    """
    Carga y formatea el contexto de coche y tramo para el LLM.

    Uso básico:
        loader = ContextLoader()
        context_text = loader.build_context(SessionContext(
            car_id="Hyundaii20NRally2",
            stage_id="Munster",
            current_setup={...}   # opcional, del fichero .sav
        ))
    """

    def __init__(self):
        self._cars_dir  = os.path.join(_DATA_DIR, "cars")
        self._stages_dir = os.path.join(_DATA_DIR, "stages")

    # ── Carga de ficheros ─────────────────────────────────────────────────────

    def load_car(self, car_id: str) -> Optional[dict]:
        """
        Carga el JSON del coche buscando por car_id.

        Busca en data/cars/ el primer fichero cuyo campo 'car_id'
        coincida con el parámetro. No distingue mayúsculas/minúsculas.

        Retorna el diccionario del JSON o None si no lo encuentra.
        """
        if not os.path.isdir(self._cars_dir):
            return None

        for filename in os.listdir(self._cars_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self._cars_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("car_id", "").lower() == car_id.lower():
                return data

        return None

    def load_stage(self, stage_id: str) -> Optional[dict]:
        """
        Carga el JSON del tramo buscando por stage_id.

        Misma lógica que load_car pero en data/stages/.
        """
        if not os.path.isdir(self._stages_dir):
            return None

        for filename in os.listdir(self._stages_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self._stages_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("stage_id", "").lower() == stage_id.lower():
                return data

        return None

    def list_cars(self) -> list[str]:
        """Devuelve los car_id de todos los coches disponibles en data/cars/."""
        ids = []
        if not os.path.isdir(self._cars_dir):
            return ids
        for filename in os.listdir(self._cars_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self._cars_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ids.append(data.get("car_id", filename))
        return ids

    def list_stages(self) -> list[str]:
        """Devuelve los stage_id de todos los tramos disponibles en data/stages/."""
        ids = []
        if not os.path.isdir(self._stages_dir):
            return ids
        for filename in os.listdir(self._stages_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self._stages_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ids.append(data.get("stage_id", filename))
        return ids

    # ── Construcción del contexto ─────────────────────────────────────────────

    def build_context(self, context: SessionContext) -> str:
        """
        Construye el bloque de texto de contexto para inyectar en el prompt.

        Combina:
            - Datos del coche (parámetros configurables + rangos)
            - Setup actual o setup base si no hay actual
            - Datos del tramo (superficie, características, hints)

        Parámetros
        ----------
        context : SessionContext
            Objeto con car_id, stage_id y setup actual (opcional).

        Retorna
        -------
        str con el contexto formateado listo para el prompt.
        """
        sections = []

        # ── Coche ─────────────────────────────────────────────────────────────
        car = self.load_car(context.car_id)
        if car:
            sections.append(self._format_car_context(car, context.current_setup))
        else:
            sections.append(f"## Coche\nID: {context.car_id} (sin datos detallados disponibles)")

        # ── Tramo ─────────────────────────────────────────────────────────────
        stage = self.load_stage(context.stage_id)
        if stage:
            sections.append(self._format_stage_context(stage))
        else:
            sections.append(f"## Tramo\nID: {context.stage_id} (sin datos detallados disponibles)")

        return "\n\n".join(sections)

    def _format_car_context(self, car: dict, current_setup: Optional[dict]) -> str:
        """Formatea los datos del coche en texto para el prompt."""
        base = car.get("setup_base", {})

        # Si hay setup actual lo usamos; si no, el setup_base del JSON
        setup = current_setup if current_setup else base

        lines = [
            f"## Coche: {car.get('display_name', car.get('car_id'))}",
            f"- Tracción: {car.get('drivetrain', 'desconocida')}",
            f"- Categoría: {car.get('category', 'desconocida')}",
            "",
            "### Setup actual en uso:",
        ]

        # Frenos
        brakes = setup.get("brakes", base.get("brakes", {}))
        if brakes:
            lines += [
                "**Frenos:**",
                f"  - Bias delantero: {brakes.get('front_bias', '?')} "
                f"(rango: {base.get('brakes', {}).get('front_bias_range', 'N/A')})",
                f"  - Cilindro maest. delantero: {brakes.get('master_cylinder_front', '?')} mm",
                f"  - Cilindro maest. trasero: {brakes.get('master_cylinder_rear', '?')} mm",
                f"  - Pastillas: {brakes.get('pad_compound', '?')}",
            ]

        # Suspensión
        suspension = setup.get("suspension", base.get("suspension", {}))
        if suspension:
            lines += [
                "**Suspensión:**",
                f"  - Muelle delantero: {suspension.get('front_spring_stiffness', '?')} N/m "
                f"(rango: {base.get('suspension', {}).get('front_spring_stiffness_range', 'N/A')})",
                f"  - Muelle trasero: {suspension.get('rear_spring_stiffness', '?')} N/m "
                f"(rango: {base.get('suspension', {}).get('rear_spring_stiffness_range', 'N/A')})",
                f"  - ARB delantero: {suspension.get('front_arb_stiffness', '?')} N/m "
                f"(rango: {base.get('suspension', {}).get('front_arb_stiffness_range', 'N/A')})",
                f"  - ARB trasero: {suspension.get('rear_arb_stiffness', '?')} N/m "
                f"(rango: {base.get('suspension', {}).get('rear_arb_stiffness_range', 'N/A')})",
            ]

        # Diferencial
        diff = setup.get("differentials", base.get("differentials", {}))
        if diff:
            lines += [
                "**Diferencial:**",
                f"  - Preload trasero: {diff.get('rear_lsd_preload', '?')} Nm "
                f"(rango: {base.get('differentials', {}).get('rear_lsd_preload_range', 'N/A')})",
                f"  - Rampas traseras: {diff.get('rear_lsd_ramps', '?')} "
                f"(opciones: {base.get('differentials', {}).get('rear_lsd_ramps_options', 'N/A')})",
                f"  - Preload delantero: {diff.get('front_lsd_preload', '?')} Nm",
                f"  - Rampas delanteras: {diff.get('front_lsd_ramps', '?')}",
            ]

        # Alineación
        alignment = setup.get("alignment", base.get("alignment", {}))
        if alignment:
            lines += [
                "**Alineación y neumáticos:**",
                f"  - Presión delantera: {alignment.get('front_tyre_pressure', '?')} PSI "
                f"(rango: {base.get('alignment', {}).get('front_tyre_pressure_range', 'N/A')})",
                f"  - Presión trasera: {alignment.get('rear_tyre_pressure', '?')} PSI",
                f"  - Camber delantero: {alignment.get('front_camber', '?')}° "
                f"(rango: {base.get('alignment', {}).get('front_camber_range', 'N/A')})",
                f"  - Camber trasero: {alignment.get('rear_camber', '?')}°",
                f"  - Toe delantero: {alignment.get('front_toe', '?')}",
                f"  - Toe trasero: {alignment.get('rear_toe', '?')}",
            ]

        # Amortiguadores
        dampers = setup.get("dampers", base.get("dampers", {}))
        if dampers:
            lines += [
                "**Amortiguadores:**",
                f"  - Bump lento: {dampers.get('slow_bump', '?')} "
                f"(rango: {base.get('dampers', {}).get('slow_bump_range', 'N/A')})",
                f"  - Rebound lento: {dampers.get('slow_rebound', '?')}",
                f"  - Bump rápido: {dampers.get('fast_bump', '?')}",
                f"  - Rebound rápido: {dampers.get('fast_rebound', '?')}",
            ]

        return "\n".join(lines)

    def _format_stage_context(self, stage: dict) -> str:
        """Formatea los datos del tramo en texto para el prompt."""
        chars = stage.get("characteristics", {})
        hints = stage.get("setup_hints", {})

        lines = [
            f"## Tramo: {stage.get('display_name', stage.get('stage_id'))}",
            f"- País: {stage.get('country', '?')}",
            f"- Superficie: {stage.get('surface', '?')}",
            f"- Notas superficie: {stage.get('surface_notes', '')}",
            "",
            "### Características del tramo:",
            f"  - Layout: {chars.get('layout', '?')}",
            f"  - Anchura: {chars.get('road_width', '?')}",
            f"  - Baches: {chars.get('bumps', '?')}",
            f"  - Peraltes: {chars.get('camber_changes', '?')}",
            f"  - Zonas de frenada: {chars.get('braking_zones', '?')}",
            "",
            "### Recomendaciones generales para este tramo:",
            f"  - Suspensión: {hints.get('suspension', '?')}",
            f"  - Neumáticos: {hints.get('tyres', '?')}",
            f"  - Frenos: {hints.get('brakes', '?')}",
            f"  - Diferencial: {hints.get('differential', '?')}",
            f"  - ARB: {hints.get('arb', '?')}",
        ]

        return "\n".join(lines)

