<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Estado-En%20Desarrollo-orange?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Plataforma-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/Juego-Assetto%20Corsa%20Rally-E8000D?style=for-the-badge"/>

# 🎯 ACR Telemetry Advisor

**Analizador de telemetría y asesor de setup para Assetto Corsa Rally**

*El primer sistema que no solo mide cómo conduces, sino que diagnostica el comportamiento de tu chasis y te dice qué cambiar en el setup — en lenguaje natural.*

[Características](#-características) • [Arquitectura](#-arquitectura) • [Instalación](#-instalación) • [Uso](#-uso) • [Hoja de ruta](#-hoja-de-ruta) • [Contribuir](#-contribuir)

---

</div>

## ¿Qué es esto?

Los simuladores de conducción modernos como **Assetto Corsa Rally (ACR)** han alcanzado un nivel de fidelidad física que los hace muy exigentes en cuanto a la configuración del vehículo. Llega un punto en que para ser competitivo ya no basta con conducir bien: hay que optimizar el setup del coche.

El problema es que interpretar la telemetría y traducirla en cambios concretos de suspensión, diferencial o neumáticos requiere conocimientos técnicos que la mayoría de pilotos amateurs no tiene.

**ACR Telemetry Advisor** resuelve exactamente ese problema.

```
Tu etapa en ACR
      │
      ▼
 [Captura de telemetría en tiempo real]
      │
      ▼
 [Motor de análisis: subviraje, sobreviraje, bloqueos, tracción]
      │
      ▼
 [LLM: genera recomendaciones de setup en lenguaje natural]
      │
      ▼
 "Se detecta subviraje en entrada de curva. Reduce la barra
  antiroll delantera de 5/7 a 3/7 para liberar el eje delantero."
```

> **¿En qué se diferencia de Track Titan o RaceData AI?**
> Esas herramientas analizan tu *técnica de conducción*. Esta analiza el *comportamiento del chasis* y te dice qué tornillo girar.

---

## ✨ Características

### Diagnóstico automático del vehículo
- 🔴 **Subviraje / sobreviraje** — detectado por diferencial de velocidades angulares entre ejes
- 🔶 **Bloqueo de frenos** — análisis rueda a rueda, tramo a tramo
- 🟡 **Patinaje de tracción** — comparativa velocidad real vs velocidad angular de ruedas motrices
- 🔵 **Consistencia** — varianza del perfil de frenada y aceleración a lo largo de la etapa

### Recomendaciones de setup con IA
- Generadas por un LLM (Claude de Anthropic) a partir de los diagnósticos
- Recomendaciones concretas: parámetro específico, dirección del cambio y justificación
- Nivel de confianza indicado en cada sugerencia

### Visualización de telemetría
- Panel en tiempo real durante la etapa
- Gráficas post-etapa por tramos
- Heatmap de incidencias sobre el perfil de velocidad

### Gestión de sesiones
- Grabación y exportación de sesiones en CSV
- Historial de etapas para seguimiento de la evolución

---

## 🏗 Arquitectura

El proyecto se organiza en cuatro capas bien diferenciadas:

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERFAZ (PyQt6)                      │
│         Panel en vivo │ Análisis post-etapa │ Setup advisor  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                  MOTOR DE RECOMENDACIONES                    │
│              Claude API (anthropic SDK)                      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    MOTOR DE ANÁLISIS                         │
│              pandas │ numpy │ algoritmos de dinámica         │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                  CAPTURA DE TELEMETRÍA                       │
│         pywin32 │ Shared Memory de Windows │ ACR             │
└─────────────────────────────────────────────────────────────┘
```

### Estructura del repositorio

```
acr-telemetry-advisor/
│
├── src/
│   ├── capture/          # Lectura de memoria compartida de ACR
│   │   └── acr_reader.py
│   │
│   ├── analysis/         # Motor de diagnóstico de comportamiento
│   │   ├── understeer.py
│   │   ├── oversteer.py
│   │   ├── braking.py
│   │   └── traction.py
│   │
│   ├── advisor/          # Integración con LLM y sistema de prompts
│   │   ├── prompt_builder.py
│   │   └── llm_client.py
│   │
│   └── ui/               # Interfaz gráfica
│       ├── main_window.py
│       ├── live_panel.py
│       └── analysis_panel.py
│
├── data/
│   └── sessions/         # Sesiones grabadas (CSV)
│
├── tests/                # Tests unitarios (pytest)
│
├── docs/                 # Documentación adicional
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Instalación

### Requisitos previos

- **Windows 10/11** (la lectura de memoria compartida es exclusiva de Windows)
- **Python 3.11 o superior** — [descargar aquí](https://www.python.org/downloads/)
- **Assetto Corsa Rally** instalado y funcionando
- Una **API key de Anthropic** para las recomendaciones de setup — [obtener aquí](https://console.anthropic.com/)

### Pasos

**1. Clona el repositorio**
```bash
git clone https://github.com/tu-usuario/acr-telemetry-advisor.git
cd acr-telemetry-advisor
```

**2. Crea y activa el entorno virtual**
```bash
python -m venv venv
venv\Scripts\activate
```

**3. Instala las dependencias**
```bash
pip install -r requirements.txt
```

**4. Configura las variables de entorno**
```bash
copy .env.example .env
```
Abre `.env` y añade tu API key de Anthropic:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**5. Ejecuta la aplicación**
```bash
python src/main.py
```

---

## 🕹 Uso

1. **Arranca ACR** y carga cualquier etapa
2. **Lanza ACR Telemetry Advisor** — detectará automáticamente el juego en ejecución
3. **Pulsa Iniciar grabación** antes de comenzar la etapa
4. Conduce la etapa con normalidad
5. Al terminar, accede al **panel de análisis** para ver los diagnósticos
6. El sistema generará automáticamente las **recomendaciones de setup**

> 💡 **Consejo:** Para que las recomendaciones sean más precisas, introduce el setup actual de tu coche en el panel de configuración antes de analizar la sesión.

---

## 🛠 Stack tecnológico

| Herramienta | Versión | Uso |
|---|---|---|
| Python | 3.11+ | Lenguaje principal |
| pywin32 | latest | Lectura de memoria compartida de Windows |
| pandas | 2.x | Manipulación y análisis de datos de telemetría |
| numpy | 1.x | Cálculos vectoriales sobre canales de datos |
| matplotlib / plotly | latest | Visualización de gráficas y heatmaps |
| anthropic | latest | SDK para llamadas a la API de Claude |
| PyQt6 | 6.x | Interfaz gráfica de escritorio |
| pytest | latest | Testing del motor de análisis |

---

## 🗺 Hoja de ruta

### v0.1 — Fundamentos *(en progreso)*
- [x] Definición de arquitectura y documentación inicial
- [ ] Configuración del entorno y estructura del proyecto
- [ ] Lectura básica de telemetría de ACR

### v0.2 — Motor de análisis
- [ ] Detección de subviraje y sobreviraje
- [ ] Detección de bloqueo de frenos
- [ ] Detección de patinaje de tracción
- [ ] Grabación y exportación de sesiones

### v0.3 — Integración con LLM
- [ ] Sistema de construcción de prompts
- [ ] Integración con Claude API
- [ ] Validación de recomendaciones contra reglas base

### v0.4 — Interfaz gráfica
- [ ] Panel en tiempo real
- [ ] Pantalla de análisis post-etapa con gráficas
- [ ] Panel de recomendaciones de setup

### v1.0 — Release inicial
- [ ] Tests unitarios completos
- [ ] Documentación de usuario
- [ ] Instalador para Windows

### Futuro (v2+)
- [ ] Soporte para otros simuladores (ACC, EA WRC)
- [ ] Dashboard web
- [ ] Comparativa entre pilotos
- [ ] Modelo propio de recomendaciones

---

## 🤝 Contribuir

Este es un proyecto personal en sus fases iniciales, pero las contribuciones son bienvenidas. Si tienes conocimientos de dinámica de vehículos de rally y quieres ayudar a refinar los algoritmos de diagnóstico, abre un issue o un pull request.

**Antes de contribuir:**
1. Abre un issue describiendo qué quieres cambiar o añadir
2. Espera confirmación antes de ponerte a trabajar
3. Sigue las convenciones de código del proyecto (PEP 8)
4. Añade tests para cualquier funcionalidad nueva

---

## ⚠️ Limitaciones conocidas

- **Solo Windows** — la lectura de memoria compartida de ACR usa APIs nativas de Windows
- **ACR en early access** — los canales de telemetría disponibles pueden cambiar con actualizaciones del juego
- **Las recomendaciones son sugerencias**, no verdades absolutas. El diagnóstico automático no puede distinguir en todos los casos si un problema es de setup o de técnica de conducción

---


<div align="center">

Hecho con 🎮 y demasiadas horas en el simulador

*Si este proyecto te resulta útil, dale una ⭐ en GitHub*

</div>
