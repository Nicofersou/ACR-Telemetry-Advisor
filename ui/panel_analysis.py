"""
panel_analysis.py
-----------------
Pantalla de análisis post-etapa — Fase 6 del proyecto.

Muestra gráficas de la telemetría usando matplotlib integrado en Qt:
    - Severidad de subviraje y sobreviraje a lo largo de la distancia.
    - Severidad de bloqueo de frenos y patinaje.
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

        # Figura de matplotlib con 2 subgráficas
        self.figure = Figure(figsize=(10, 5), facecolor="#1a1a2e")
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
        Dibuja las dos gráficas de severidad por distancia.

        La figura tiene 2 subplots (filas) compartiendo el eje X (distancia):
            - Superior: subviraje (rojo) y sobreviraje (naranja)
            - Inferior: bloqueo de frenos (azul) y patinaje (verde)
        """
        self.figure.clear()

        # Colores del tema oscuro
        bg      = "#1a1a2e"
        grid_c  = "#2a2a4e"
        text_c  = "#aaaacc"

        # Organizamos los incidentes por tipo para graficarlos
        # Usamos listas de (distancia, severidad) para cada tipo
        data = {
            "understeer":    ([], []),
            "oversteer":     ([], []),
            "brake_lock":    ([], []),
            "traction_slip": ([], []),
        }
        for inc in report.incidents:
            if inc.incident_type in data:
                data[inc.incident_type][0].append(inc.stage_distance / 1000)  # km
                data[inc.incident_type][1].append(inc.severity)

        # Crear subplots
        ax1, ax2 = self.figure.subplots(2, 1, sharex=True)

        for ax in (ax1, ax2):
            ax.set_facecolor(bg)
            ax.tick_params(colors=text_c)
            ax.spines["bottom"].set_color(grid_c)
            ax.spines["top"].set_color(grid_c)
            ax.spines["left"].set_color(grid_c)
            ax.spines["right"].set_color(grid_c)
            ax.yaxis.label.set_color(text_c)
            ax.xaxis.label.set_color(text_c)
            ax.set_ylim(0, 1.05)
            ax.grid(True, color=grid_c, linewidth=0.5)
            ax.set_ylabel("Severidad", fontsize=9, color=text_c)

        # Gráfica superior: subviraje y sobreviraje
        self._plot_incidents(ax1, data["understeer"],  "#e94560", "Subviraje")
        self._plot_incidents(ax1, data["oversteer"],   "#f5a623", "Sobreviraje")
        ax1.legend(facecolor="#16213e", labelcolor=text_c, fontsize=9)
        ax1.set_title("Comportamiento dinámico por distancia", color=text_c, fontsize=10, pad=8)

        # Gráfica inferior: frenos y tracción
        self._plot_incidents(ax2, data["brake_lock"],    "#4a9eff", "Bloqueo frenos")
        self._plot_incidents(ax2, data["traction_slip"], "#7ed321", "Patinaje tracción")
        ax2.legend(facecolor="#16213e", labelcolor=text_c, fontsize=9)
        ax2.set_xlabel("Distancia en etapa (km)", fontsize=9, color=text_c)

        self.figure.tight_layout(pad=1.5)
        self.canvas.draw()

    def _plot_incidents(self, ax, data: tuple, color: str, label: str):
        """Dibuja los puntos de incidentes de un tipo en un eje."""
        distances, severities = data
        if distances:
            ax.scatter(distances, severities, color=color, label=label,
                       alpha=0.75, s=20, zorder=3)
            # Línea de tendencia suavizada (media móvil simple)
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
            "understeer":    "#e94560",
            "oversteer":     "#f5a623",
            "brake_lock":    "#4a9eff",
            "traction_slip": "#7ed321",
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

            tipo_lbl = QLabel(inc.incident_type.replace("_", " ").title())
            tipo_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

            dist_lbl = QLabel(f"{inc.stage_distance / 1000:.2f} km")
            dist_lbl.setStyleSheet("color: #cccccc; font-size: 12px;")

            sev_lbl = QLabel(f"{inc.severity:.0%}")
            sev_lbl.setStyleSheet("color: #ffffff; font-size: 12px;")

            detail_lbl = QLabel(inc.detail)
            detail_lbl.setStyleSheet("color: #888888; font-size: 11px;")

            row_layout.addWidget(tipo_lbl, 2)
            row_layout.addWidget(dist_lbl, 2)
            row_layout.addWidget(sev_lbl, 2)
            row_layout.addWidget(detail_lbl, 5)

            self.incidents_layout.addWidget(row)

