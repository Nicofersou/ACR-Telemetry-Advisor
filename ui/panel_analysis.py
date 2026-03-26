"""
panel_analysis.py
-----------------
Pantalla de análisis post-etapa — Fase 6 del proyecto.

Muestra gráficas de la telemetría usando matplotlib integrado en Qt:
    - Severidad de subviraje y sobreviraje a lo largo de la distancia.
    - Severidad de bloqueo de frenos y patinaje.
    - Gráfica de pedales: posición de acelerador (verde) y freno (rojo).
    - Tabla resumen con los peores incidentes.

Cómo se integra matplotlib en Qt:
    matplotlib tiene un backend llamado 'Qt6Agg' que permite incrustar
    una figura de matplotlib dentro de un widget de Qt. Es como poner
    un JPanel en Java dentro de un JFrame.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use("QtAgg")   # decimos a matplotlib que use el backend de Qt (detecta Qt6 automáticamente)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from analysis.session_analyzer import SessionReport


class AnalysisPanel(QWidget):
    """
    Panel de análisis post-etapa con gráficas de telemetría.

    Se actualiza llamando a update_report(report) desde MainWindow
    una vez que el análisis termina.
    """

    def __init__(self):
        super().__init__()
        self._build_ui()

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        """Construye el layout del panel con zona de gráficas y tabla."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        # Título
        lbl = QLabel("Análisis de Sesión")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(lbl)

        # Mensaje mientras no hay datos
        self.lbl_empty = QLabel("Ejecuta una sesión desde el Panel de Sesión para ver el análisis.")
        self.lbl_empty.setStyleSheet("color: #888888; font-size: 13px;")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_empty)

        # Contenedor de gráficas (oculto hasta que lleguen datos)
        self.charts_container = QWidget()
        self.charts_container.hide()
        charts_layout = QVBoxLayout(self.charts_container)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(12)

        # Figura de matplotlib con 3 subgráficas (antes eran 2)
        self.figure = Figure(figsize=(10, 7), facecolor="#1a1a2e")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        charts_layout.addWidget(self.canvas)

        # Tabla de incidentes (área con scroll)
        charts_layout.addWidget(self._build_incidents_table_header())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.incidents_table = QWidget()
        self.incidents_layout = QVBoxLayout(self.incidents_table)
        self.incidents_layout.setContentsMargins(0, 0, 0, 0)
        self.incidents_layout.setSpacing(4)
        scroll.setWidget(self.incidents_table)
        charts_layout.addWidget(scroll)

        layout.addWidget(self.charts_container)

    def _build_incidents_table_header(self) -> QWidget:
        """Cabecera de la tabla de incidentes."""
        header = QWidget()
        header.setStyleSheet("background-color: #16213e; border-radius: 6px;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)

        for text, stretch in [("Tipo", 2), ("Distancia (km)", 2), ("Severidad", 2), ("Detalle", 5)]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")
            layout.addWidget(lbl, stretch)

        return header

    # ── Actualización de datos ────────────────────────────────────────────────

    def update_report(self, report: SessionReport):
        """
        Recibe el SessionReport y redibuja las gráficas y la tabla.

        Parámetros
        ----------
        report : SessionReport
            Resultado del análisis de SessionAnalyzer.
        """
        self.lbl_empty.hide()
        self.charts_container.show()

        self._draw_charts(report)
        self._populate_incidents_table(report)

    def _draw_charts(self, report: SessionReport):
        """
        Dibuja tres gráficas de telemetría compartiendo el eje X (distancia):
            1. Subviraje y sobreviraje (solo no-inducido)
            2. Bloqueo de frenos y patinaje de tracción
            3. Pedales: acelerador (verde) y freno (rojo)
        """
        self.figure.clear()

        # Colores del tema oscuro
        bg     = "#1a1a2e"
        grid_c = "#2a2a4e"
        text_c = "#aaaacc"

        # ── Organizar incidentes por tipo para las gráficas 1 y 2 ─────────
        data = {
            "understeer":              ([], []),
            "oversteer_driver_error":  ([], []),  # sobreviraje no intencionado
            "oversteer_setup":         ([], []),  # sobreviraje de setup (resumen)
            "brake_lock":              ([], []),
            "traction_slip":           ([], []),
        }
        for inc in report.incidents:
            # oversteer_induced no se grafica (es técnica, no problema)
            if inc.incident_type in data:
                data[inc.incident_type][0].append(inc.stage_distance / 1000)  # km
                data[inc.incident_type][1].append(inc.severity)

        # ── Crear 3 subplots que comparten eje X ──────────────────────────
        # gridspec_kw permite dar alturas relativas distintas a cada subplot.
        # El de pedales (ax3) lo hacemos un poco más pequeño.
        ax1, ax2, ax3 = self.figure.subplots(
            3, 1, sharex=True,
            gridspec_kw={"height_ratios": [2, 2, 1.5]}
        )

        for ax in (ax1, ax2, ax3):
            ax.set_facecolor(bg)
            ax.tick_params(colors=text_c)
            for spine in ax.spines.values():
                spine.set_color(grid_c)
            ax.yaxis.label.set_color(text_c)
            ax.xaxis.label.set_color(text_c)
            ax.grid(True, color=grid_c, linewidth=0.5)
            ax.set_ylabel("Severidad", fontsize=9, color=text_c)

        # ── Gráfica 1: Subviraje y sobreviraje ────────────────────────────
        ax1.set_ylim(0, 1.05)
        self._plot_incidents(ax1, data["understeer"],             "#e94560", "Subviraje")
        self._plot_incidents(ax1, data["oversteer_driver_error"], "#f5a623", "Sobreviraje (no inducido)")
        self._plot_incidents(ax1, data["oversteer_setup"],        "#ff6b35", "Sobreviraje Setup ⚠")
        ax1.legend(facecolor="#16213e", labelcolor=text_c, fontsize=9)
        ax1.set_title("Comportamiento dinámico por distancia", color=text_c, fontsize=10, pad=8)

        # Nota: el sobreviraje inducido (técnica de rally) NO se muestra aquí
        # porque no es un problema; sería ruido visual innecesario.

        # ── Gráfica 2: Frenos y tracción ──────────────────────────────────
        ax2.set_ylim(0, 1.05)
        self._plot_incidents(ax2, data["brake_lock"],    "#4a9eff", "Bloqueo frenos")
        self._plot_incidents(ax2, data["traction_slip"], "#7ed321", "Patinaje tracción")
        ax2.legend(facecolor="#16213e", labelcolor=text_c, fontsize=9)
        ax2.set_ylabel("Severidad", fontsize=9, color=text_c)

        # ── Gráfica 3: Pedales ────────────────────────────────────────────
        # pedal_data es lista de tuplas (dist_km, throttle, brake)
        ax3.set_ylim(-0.05, 1.10)
        ax3.set_ylabel("Input", fontsize=9, color=text_c)

        if report.pedal_data:
            # Desempaquetar: zip(*lista) es el equivalente a "transponer" la lista
            distances, throttles, brakes = zip(*report.pedal_data)

            # Rellenamos con área bajo la curva para que sea más visual
            # fill_between pinta el área entre 0 y el valor de cada punto
            ax3.fill_between(distances, throttles, 0,
                             color="#7ed321", alpha=0.55, label="Acelerador")
            ax3.fill_between(distances, brakes, 0,
                             color="#e94560", alpha=0.55, label="Freno")

            # Línea encima para mayor definición
            ax3.plot(distances, throttles, color="#7ed321", linewidth=0.8, alpha=0.9)
            ax3.plot(distances, brakes,    color="#e94560", linewidth=0.8, alpha=0.9)

        ax3.legend(facecolor="#16213e", labelcolor=text_c, fontsize=9)
        ax3.set_xlabel("Distancia en etapa (km)", fontsize=9, color=text_c)

        self.figure.tight_layout(pad=1.5)
        self.canvas.draw()

    def _plot_incidents(self, ax, data: tuple, color: str, label: str):
        """Dibuja los puntos de incidentes de un tipo en un eje."""
        distances, severities = data
        if distances:
            ax.scatter(distances, severities, color=color, label=label,
                       alpha=0.75, s=20, zorder=3)
            # Línea de tendencia suavizada
            if len(distances) >= 3:
                sorted_pairs = sorted(zip(distances, severities))
                xs = [p[0] for p in sorted_pairs]
                ys = [p[1] for p in sorted_pairs]
                ax.plot(xs, ys, color=color, alpha=0.3, linewidth=1)
        else:
            ax.scatter([], [], color=color, label=label, s=20)

    def _populate_incidents_table(self, report: SessionReport):
        """Rellena la tabla con los incidentes ordenados por severidad."""
        # Limpiamos la tabla anterior
        for i in reversed(range(self.incidents_layout.count())):
            widget = self.incidents_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        color_map = {
            "understeer":              "#e94560",
            "oversteer_induced":       "#888888",   # gris: no es un problema
            "oversteer_driver_error":  "#f5a623",
            "oversteer_setup":         "#ff6b35",
            "brake_lock":              "#4a9eff",
            "traction_slip":           "#7ed321",
        }

        # Etiquetas más legibles para mostrar en la tabla
        label_map = {
            "understeer":              "Subviraje",
            "oversteer_induced":       "Sobreviraje Inducido ✓",
            "oversteer_driver_error":  "Sobreviraje Error",
            "oversteer_setup":         "⚠ Sobreviraje Setup",
            "brake_lock":              "Bloqueo Frenos",
            "traction_slip":           "Patinaje Tracción",
        }

        sorted_incidents = sorted(report.incidents, key=lambda x: x.severity, reverse=True)

        for inc in sorted_incidents[:20]:   # máximo 20 filas
            row = QWidget()
            row.setStyleSheet("""
                QWidget { background-color: #16213e; border-radius: 4px; }
                QWidget:hover { background-color: #1e2a4e; }
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 6, 12, 6)

            color = color_map.get(inc.incident_type, "#ffffff")
            label = label_map.get(inc.incident_type, inc.incident_type.replace("_", " ").title())

            tipo_lbl = QLabel(label)
            tipo_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

            dist_lbl = QLabel(f"{inc.stage_distance / 1000:.2f} km")
            dist_lbl.setStyleSheet("color: #cccccc; font-size: 12px;")

            sev_lbl = QLabel(f"{inc.severity:.0%}")
            sev_lbl.setStyleSheet("color: #ffffff; font-size: 12px;")

            detail_lbl = QLabel(inc.detail)
            detail_lbl.setStyleSheet("color: #888888; font-size: 11px;")
            detail_lbl.setWordWrap(True)

            row_layout.addWidget(tipo_lbl, 2)
            row_layout.addWidget(dist_lbl, 2)
            row_layout.addWidget(sev_lbl, 2)
            row_layout.addWidget(detail_lbl, 5)

            self.incidents_layout.addWidget(row)
