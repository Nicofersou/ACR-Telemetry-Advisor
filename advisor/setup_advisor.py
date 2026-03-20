"""
setup_advisor.py
----------------
Capa de Generación de Recomendaciones — Fase 5 del proyecto.

Responsabilidad: recibir el resumen de diagnósticos del motor de análisis,
construir un prompt estructurado y llamar a la API de Claude (Anthropic)
para obtener recomendaciones de setup en lenguaje natural.

TODO (Fase 5):
- Refinar el prompt base con conocimiento de dinámica de vehículos rally.
- Implementar validación de recomendaciones contra reglas base antes de mostrarlas.
- Gestionar errores de la API (rate limit, timeout, etc.).
"""

from dataclasses import dataclass


SYSTEM_PROMPT = """Eres un ingeniero de setup experto en rally y dinámica de vehículos.
Tu tarea es analizar los datos de telemetría de una etapa de rally y recomendar
cambios concretos de configuración del vehículo para mejorar su comportamiento.
Usa lenguaje claro y accesible para pilotos sin formación técnica.
Indica siempre el nivel de confianza de tus recomendaciones (bajo/medio/alto).
Presenta las recomendaciones como sugerencias, nunca como verdades absolutas."""


@dataclass
class DiagnosisSummary:
    understeer_severity: float       # 0.0–1.0
    oversteer_severity: float        # 0.0–1.0
    brake_lock_severity: float       # 0.0–1.0
    traction_slip_severity: float    # 0.0–1.0
    stage_surface: str               # "gravel", "tarmac", "snow", "mixed"
    current_setup_notes: str         # descripción libre del setup actual


class SetupAdvisor:
    """Genera recomendaciones de setup usando la API de Claude de Anthropic."""

    def __init__(self, api_key: str):
        # TODO: inicializar cliente anthropic en Fase 5
        self._api_key = api_key
        self._client = None

    def _build_prompt(self, diagnosis: DiagnosisSummary) -> str:
        """Construye el prompt estructurado a partir del diagnóstico."""
        return f"""
## Datos de la sesión
- Superficie: {diagnosis.stage_surface}
- Setup actual: {diagnosis.current_setup_notes}

## Diagnóstico detectado
- Subviraje (severidad {diagnosis.understeer_severity:.0%})
- Sobreviraje (severidad {diagnosis.oversteer_severity:.0%})
- Bloqueo de frenos (severidad {diagnosis.brake_lock_severity:.0%})
- Patinaje de tracción (severidad {diagnosis.traction_slip_severity:.0%})

## Tarea
Proporciona recomendaciones concretas de setup para corregir los problemas detectados.
"""

    def get_recommendations(self, diagnosis: DiagnosisSummary) -> str:
        """
        Llama a la API de Claude y devuelve las recomendaciones como texto.

        TODO (Fase 5): implementar la llamada real a anthropic.
        """
        raise NotImplementedError("Integración con Claude pendiente (Fase 5)")

