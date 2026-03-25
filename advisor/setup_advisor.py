"""
setup_advisor.py
----------------
Capa de Generación de Recomendaciones — Fase 5/7 del proyecto.

Responsabilidad: recibir el SessionReport + SessionContext, construir un
prompt enriquecido con los datos del coche y el tramo, y llamar a Ollama.

Flujo:
    SessionReport + SessionContext
        → SetupAdvisor.get_recommendations()
        → str (recomendaciones personalizadas)
"""

import ollama
from analysis.session_analyzer import SessionReport
from data.context_loader import ContextLoader, SessionContext


# ─── Prompt base del sistema ──────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un ingeniero de setup experto en rally y dinámica de vehículos.
Tu tarea es analizar los datos de telemetría de una etapa de rally y recomendar
cambios concretos de configuración del vehículo para mejorar su comportamiento.
Usa lenguaje claro y accesible para pilotos sin formación técnica.
Cuando sugieras un cambio, indica SIEMPRE el valor actual y el valor recomendado.
Indica el nivel de confianza de cada recomendación (bajo/medio/alto).
Presenta las recomendaciones como sugerencias, nunca como verdades absolutas.
Responde siempre en español."""


# ─── Clase principal ──────────────────────────────────────────────────────────

class SetupAdvisor:
    """
    Genera recomendaciones de setup usando un modelo local a través de Ollama.

    Uso básico (sin contexto):
        advisor = SetupAdvisor()
        texto = advisor.get_recommendations(report)

    Uso completo (con coche y tramo):
        advisor = SetupAdvisor()
        ctx = SessionContext(car_id="Hyundaii20NRally2", stage_id="Munster")
        texto = advisor.get_recommendations(report, context=ctx)
    """

    MODEL = "llama3.1:8b"

    def __init__(self, model: str = None):
        if model:
            self.MODEL = model
        self._context_loader = ContextLoader()

    def _build_prompt(self, report: SessionReport, context: SessionContext = None) -> str:
        """
        Construye el prompt completo combinando:
          1. Contexto del coche y tramo (si existe)
          2. Diagnóstico de telemetría del SessionReport
          3. Instrucciones de tarea para el LLM
        """
        sections = []

        # ── Bloque 1: Contexto del coche y tramo ──────────────────────────────
        if context:
            context_text = self._context_loader.build_context(context)
            sections.append(context_text)
        else:
            sections.append("## Coche y tramo\nNo se proporcionó información de coche/tramo.")

        # ── Bloque 2: Diagnóstico de telemetría ───────────────────────────────
        understeer_count  = sum(1 for i in report.incidents if i.incident_type == "understeer")
        oversteer_count   = sum(1 for i in report.incidents if i.incident_type == "oversteer")
        brake_lock_count  = sum(1 for i in report.incidents if i.incident_type == "brake_lock")
        traction_count    = sum(1 for i in report.incidents if i.incident_type == "traction_slip")

        worst_incidents = sorted(report.incidents, key=lambda x: x.severity, reverse=True)[:5]
        incidents_text = "\n".join(
            f"  - [{inc.incident_type}] km {inc.stage_distance / 1000:.2f} "
            f"| severidad {inc.severity:.0%} | {inc.detail}"
            for inc in worst_incidents
        ) or "  Ninguno detectado"

        sections.append(f"""## Datos de telemetría de la sesión

- Superficie detectada : {report.surface or 'desconocida'}
- Distancia total      : {report.stage_distance_m:.0f} m
- Frames analizados    : {report.total_frames}
- Total incidentes     : {report.total_incidents}

### Severidad media por comportamiento:
| Comportamiento       | Severidad | Nº incidentes |
|----------------------|-----------|---------------|
| Subviraje            | {report.avg_understeer_severity:.0%}     | {understeer_count} |
| Sobreviraje          | {report.avg_oversteer_severity:.0%}     | {oversteer_count} |
| Bloqueo de frenos    | {report.avg_brake_lock_severity:.0%}     | {brake_lock_count} |
| Patinaje de tracción | {report.avg_traction_slip_severity:.0%}     | {traction_count} |

### Peores incidentes:
{incidents_text}""")

        # ── Bloque 3: Instrucciones de tarea ──────────────────────────────────
        sections.append("""## Tu tarea

Basándote en el setup actual del coche, las características del tramo y los datos de telemetría:
1. Identifica los 2-3 problemas más importantes.
2. Para cada problema, indica el parámetro a cambiar, su valor actual y el valor recomendado.
3. Explica brevemente por qué ese cambio mejorará el comportamiento.
4. Indica el nivel de confianza (bajo/medio/alto).
5. Máximo 250 palabras en total.""")

        return "\n\n".join(sections)

    def get_recommendations(self, report: SessionReport, context: SessionContext = None) -> str:
        """
        Llama a Ollama con el informe y el contexto, devuelve recomendaciones.

        Parámetros
        ----------
        report : SessionReport
            Resultado del análisis de SessionAnalyzer.
        context : SessionContext, opcional
            Información del coche y tramo para enriquecer el prompt.

        Retorna
        -------
        str con las recomendaciones en lenguaje natural.
        """
        prompt = self._build_prompt(report, context)

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
