"""
setup_advisor.py
----------------
Capa de Generación de Recomendaciones — Fase 5 del proyecto.

Responsabilidad: recibir el SessionReport del motor de análisis,
construir un prompt estructurado y llamar al modelo local Ollama
para obtener recomendaciones de setup en lenguaje natural.

Flujo:
    SessionReport → SetupAdvisor.get_recommendations() → str (recomendaciones)
"""

import ollama
from analysis.session_analyzer import SessionReport


# ─── Prompt base del sistema ──────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un ingeniero de setup experto en rally y dinámica de vehículos.
Tu tarea es analizar los datos de telemetría de una etapa de rally y recomendar
cambios concretos de configuración del vehículo para mejorar su comportamiento.
Usa lenguaje claro y accesible para pilotos sin formación técnica.
Indica siempre el nivel de confianza de tus recomendaciones (bajo/medio/alto).
Presenta las recomendaciones como sugerencias, nunca como verdades absolutas."""


# ─── Clase principal ──────────────────────────────────────────────────────────

class SetupAdvisor:
    """
    Genera recomendaciones de setup usando un modelo local a través de Ollama.

    Uso básico:
        advisor = SetupAdvisor()
        recomendaciones = advisor.get_recommendations(report)
        print(recomendaciones)
    """

    MODEL = "llama3.1:8b"

    def __init__(self, model: str = None):
        """
        Parámetros
        ----------
        model : str, opcional
            Nombre del modelo Ollama a usar. Por defecto "llama3.1:8b".
        """
        if model:
            self.MODEL = model

    def _build_prompt(self, report: SessionReport) -> str:
        """
        Construye el prompt estructurado a partir del SessionReport.

        Toma los datos ya procesados por el motor de análisis y los
        convierte en un texto que el LLM pueda entender y responder.

        Parámetros
        ----------
        report : SessionReport
            Informe generado por SessionAnalyzer.analyze()

        Retorna
        -------
        str con el prompt listo para enviar al modelo.
        """

        # Calculamos cuántos incidentes hay de cada tipo para dar contexto
        understeer_count  = sum(1 for i in report.incidents if i.incident_type == "understeer")
        oversteer_count   = sum(1 for i in report.incidents if i.incident_type == "oversteer")
        brake_lock_count  = sum(1 for i in report.incidents if i.incident_type == "brake_lock")
        traction_count    = sum(1 for i in report.incidents if i.incident_type == "traction_slip")

        # Tomamos los 3 incidentes más graves de cada tipo para dar ejemplos concretos
        worst_incidents = sorted(report.incidents, key=lambda x: x.severity, reverse=True)[:5]
        incidents_text = "\n".join(
            f"  - [{inc.incident_type}] km {inc.stage_distance / 1000:.2f} "
            f"| severidad {inc.severity:.0%} | {inc.detail}"
            for inc in worst_incidents
        ) or "  Ninguno detectado"

        prompt = f"""
## Datos de la sesión de telemetría

- Superficie de la etapa : {report.surface or 'desconocida'}
- Distancia total        : {report.stage_distance_m:.0f} m
- Frames analizados      : {report.total_frames}
- Total de incidentes    : {report.total_incidents}

## Diagnóstico de comportamiento detectado

| Comportamiento       | Severidad media | Nº incidentes |
|----------------------|-----------------|---------------|
| Subviraje            | {report.avg_understeer_severity:.0%}          | {understeer_count}             |
| Sobreviraje          | {report.avg_oversteer_severity:.0%}          | {oversteer_count}             |
| Bloqueo de frenos    | {report.avg_brake_lock_severity:.0%}          | {brake_lock_count}             |
| Patinaje de tracción | {report.avg_traction_slip_severity:.0%}          | {traction_count}             |

## Peores incidentes de la sesión

{incidents_text}

## Tu tarea

Basándote en los datos anteriores:
1. Identifica los 2-3 problemas más importantes que tiene el vehículo.
2. Para cada problema, proporciona una recomendación concreta de setup para corregirlo.
3. Indica el nivel de confianza de cada recomendación (bajo / medio / alto).
4. Sé breve y directo, máximo 200 palabras en total.
"""
        return prompt.strip()

    def get_recommendations(self, report: SessionReport) -> str:
        """
        Llama a Ollama con el informe de sesión y devuelve las recomendaciones.

        Parámetros
        ----------
        report : SessionReport
            Informe generado por SessionAnalyzer.analyze()

        Retorna
        -------
        str con las recomendaciones de setup en lenguaje natural.

        Lanza
        -----
        ConnectionError si Ollama no está corriendo en local.
        """
        prompt = self._build_prompt(report)

        try:
            response = ollama.chat(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ]
            )
            return response["message"]["content"]

        except Exception as e:
            raise ConnectionError(
                f"No se pudo conectar con Ollama. "
                f"¿Está Ollama corriendo en local? Error: {e}"
            )
