"""
main_window.py
--------------
Capa de Interfaz — Fase 6 del proyecto.

Ventana principal de ACR Telemetry Advisor. Contiene 3 pantallas navegables:
    1. Panel de sesión    — Iniciar/parar análisis, resumen de incidentes.
    2. Panel de análisis  — Gráficas de telemetría por distancia.
    3. Recomendaciones    — Texto generado por Ollama.

Tecnología: PyQt6 + matplotlib integrado en Qt.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QStackedWidget,
    QProgressBar, QFrame, QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont

from capture.mock_data import generate_session_frames
from analysis.session_analyzer import SessionAnalyzer, SessionReport
from advisor.setup_advisor import SetupAdvisor
from data.context_loader import ContextLoader, SessionContext
from ui.panel_analysis import AnalysisPanel
from ui.panel_recommendations import RecommendationsPanel


# ─── Hilo de trabajo para no bloquear la UI ───────────────────────────────────

class AnalysisWorker(QThread):
    """
    Ejecuta el análisis y la llamada a Ollama en un hilo secundario.

    Ahora acepta un SessionContext para enriquecer el prompt con los
    datos reales del coche y el tramo seleccionados por el usuario.
    """
    analysis_done        = pyqtSignal(object)
    recommendations_done = pyqtSignal(str)
    error_occurred       = pyqtSignal(str)

    def __init__(self, context: SessionContext = None):
        super().__init__()
        # Guardamos el contexto que nos pasa MainWindow
        self.context = context

    def run(self):
        """Este método se ejecuta en el hilo secundario."""
        try:
            frames = generate_session_frames()
            analyzer = SessionAnalyzer()
            report = analyzer.analyze(frames)
            self.analysis_done.emit(report)

            advisor = SetupAdvisor()
            # Pasamos el contexto al advisor — puede ser None si no se seleccionó
            recommendations = advisor.get_recommendations(report, context=self.context)
            self.recommendations_done.emit(recommendations)

        except ConnectionError as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"Error inesperado: {e}")


# ─── Ventana principal ────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    QMainWindow es la clase base de PyQt6 para ventanas con barra de menú,
    barra de estado, etc. Equivale a un JFrame en Java Swing.
    """

    def __init__(self):
        super().__init__()
        self.report: SessionReport | None = None
        self.worker: AnalysisWorker | None = None
        self._context_loader = ContextLoader()

        self._setup_window()
        self._setup_styles()
        self._build_ui()

    # ── Configuración inicial ─────────────────────────────────────────────────

    def _setup_window(self):
        """Configura título, tamaño y propiedades de la ventana."""
        self.setWindowTitle("ACR Telemetry Advisor")
        self.setMinimumSize(1024, 680)
        self.resize(1200, 750)

    def _setup_styles(self):
        """Aplica el tema oscuro a toda la aplicación."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c73652;
            }
            QPushButton:disabled {
                background-color: #444466;
                color: #888888;
            }
            QPushButton#nav_btn {
                background-color: transparent;
                color: #aaaacc;
                border-bottom: 2px solid transparent;
                border-radius: 0px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton#nav_btn:checked {
                color: #e94560;
                border-bottom: 2px solid #e94560;
            }
            QPushButton#nav_btn:hover {
                color: #ffffff;
                background-color: transparent;
            }
            QLabel#title {
                font-size: 20px;
                font-weight: bold;
                color: #e94560;
            }
            QLabel#subtitle {
                font-size: 12px;
                color: #888888;
            }
            QFrame#separator {
                background-color: #2a2a4e;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #2a2a4e;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #e94560;
                border-radius: 4px;
            }
        """)

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        """
        Construye toda la estructura visual de la ventana.

        Layout principal:
            [Header con título y nav]
            [Separador]
            [Contenido — QStackedWidget con las 3 pantallas]
            [Barra de estado inferior]
        """
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        main_layout.addWidget(self._build_header())

        # Separador
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        main_layout.addWidget(sep)

        # Contenido con las pantallas
        self.stack = QStackedWidget()
        self.session_panel = self._build_session_panel()
        self.analysis_panel = AnalysisPanel()
        self.recommendations_panel = RecommendationsPanel()

        self.stack.addWidget(self.session_panel)       # índice 0
        self.stack.addWidget(self.analysis_panel)      # índice 1
        self.stack.addWidget(self.recommendations_panel)  # índice 2
        main_layout.addWidget(self.stack)

        # Barra de progreso inferior (oculta por defecto)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # modo indeterminado (animación continua)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Navegamos al panel de sesión por defecto
        self._navigate(0)

    def _build_header(self) -> QWidget:
        """Construye la barra superior con logo, título y botones de navegación."""
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #16213e;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        # Título
        title_block = QVBoxLayout()
        lbl_title = QLabel("ACR Telemetry Advisor")
        lbl_title.setObjectName("title")
        lbl_subtitle = QLabel("Assetto Corsa Rally — Analizador de setup")
        lbl_subtitle.setObjectName("subtitle")
        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_subtitle)
        layout.addLayout(title_block)

        layout.addStretch()

        # Botones de navegación
        self.nav_buttons = []
        nav_items = [
            ("🏁  Sesión",         0),
            ("📊  Análisis",       1),
            ("💡  Recomendaciones", 2),
        ]
        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setFixedHeight(70)
            # lambda con default arg para capturar el valor de index en el bucle
            # En Java sería un ActionListener anónimo con la variable final
            btn.clicked.connect(lambda checked, i=index: self._navigate(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        return header

    def _build_session_panel(self) -> QWidget:
        """
        Construye el panel de sesión (pantalla 1).
        Muestra el botón de inicio y el resumen de resultados.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Título del panel
        lbl = QLabel("Panel de Sesión")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(lbl)

        desc = QLabel(
            "Pulsa el botón para analizar una sesión con datos simulados.\n"
            "En la versión final, se conectará con la telemetría en tiempo real de ACR."
        )
        desc.setStyleSheet("color: #888888; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Selectores de coche y tramo ───────────────────────────────────────
        selectors_layout = QHBoxLayout()
        selectors_layout.setSpacing(16)

        combo_style = """
            QComboBox {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #2a2a4e;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 200px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #e0e0e0;
                selection-background-color: #e94560;
            }
        """

        # Selector de coche
        car_block = QVBoxLayout()
        car_block.addWidget(QLabel("Coche:"))
        self.combo_car = QComboBox()
        self.combo_car.setStyleSheet(combo_style)
        cars = self._context_loader.list_cars()
        self.combo_car.addItem("— Sin seleccionar —", userData=None)
        for car_id in cars:
            self.combo_car.addItem(car_id, userData=car_id)
        # Preseleccionar el Hyundai si está disponible
        idx = self.combo_car.findData("Hyundaii20NRally2")
        if idx >= 0:
            self.combo_car.setCurrentIndex(idx)
        car_block.addWidget(self.combo_car)
        selectors_layout.addLayout(car_block)

        # Selector de tramo
        stage_block = QVBoxLayout()
        stage_block.addWidget(QLabel("Tramo:"))
        self.combo_stage = QComboBox()
        self.combo_stage.setStyleSheet(combo_style)
        stages = self._context_loader.list_stages()
        self.combo_stage.addItem("— Sin seleccionar —", userData=None)
        for stage_id in stages:
            self.combo_stage.addItem(stage_id, userData=stage_id)
        stage_block.addWidget(self.combo_stage)
        selectors_layout.addLayout(stage_block)

        selectors_layout.addStretch()
        layout.addLayout(selectors_layout)

        # Botón principal
        self.btn_start = QPushButton("▶  Analizar sesión")
        self.btn_start.setFixedWidth(220)
        self.btn_start.setFixedHeight(44)
        self.btn_start.clicked.connect(self._start_analysis)
        layout.addWidget(self.btn_start)

        # Tarjetas de métricas (se rellenan tras el análisis)
        self.metrics_widget = self._build_metrics_cards()
        self.metrics_widget.hide()
        layout.addWidget(self.metrics_widget)

        # Etiqueta de estado
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()
        return panel

    def _build_metrics_cards(self) -> QWidget:
        """Construye las 4 tarjetas de métricas del resumen."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(16)

        self.metric_labels = {}
        metrics = [
            ("understeer",    "Subviraje",           "#e94560"),
            ("oversteer",     "Sobreviraje",          "#f5a623"),
            ("brake_lock",    "Bloqueo de frenos",    "#4a9eff"),
            ("traction_slip", "Patinaje de tracción", "#7ed321"),
        ]

        for key, name, color in metrics:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #16213e;
                    border-left: 4px solid {color};
                    border-radius: 6px;
                    padding: 4px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")

            lbl_value = QLabel("—")
            lbl_value.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")

            lbl_count = QLabel("")
            lbl_count.setStyleSheet("color: #888888; font-size: 11px;")

            card_layout.addWidget(lbl_name)
            card_layout.addWidget(lbl_value)
            card_layout.addWidget(lbl_count)

            self.metric_labels[key] = (lbl_value, lbl_count)
            layout.addWidget(card)

        return container

    # ── Lógica de navegación ──────────────────────────────────────────────────

    def _navigate(self, index: int):
        """
        Cambia la pantalla visible en el QStackedWidget y actualiza
        el estado visual de los botones de navegación.
        """
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    # ── Lógica de análisis ────────────────────────────────────────────────────

    def _start_analysis(self):
        """
        Lanza el análisis en un hilo secundario.
        Lee los selectores de coche y tramo para construir el SessionContext.
        """
        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳  Analizando...")
        self.lbl_status.setText("Procesando frames de telemetría...")
        self.progress_bar.show()
        self.metrics_widget.hide()

        # Construir el contexto desde los selectores
        car_id   = self.combo_car.currentData()
        stage_id = self.combo_stage.currentData()
        context  = SessionContext(car_id=car_id, stage_id=stage_id) if car_id and stage_id else None

        self.worker = AnalysisWorker(context=context)
        self.worker.analysis_done.connect(self._on_analysis_done)
        self.worker.recommendations_done.connect(self._on_recommendations_done)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_analysis_done(self, report: SessionReport):
        """
        Se llama automáticamente cuando el hilo termina el análisis.
        Recibe el SessionReport y actualiza la UI con los resultados.
        """
        self.report = report

        # Actualizar tarjetas de métricas
        incident_counts = {}
        for inc in report.incidents:
            incident_counts[inc.incident_type] = incident_counts.get(inc.incident_type, 0) + 1

        severity_map = {
            "understeer":    report.avg_understeer_severity,
            "oversteer":     report.avg_oversteer_severity,
            "brake_lock":    report.avg_brake_lock_severity,
            "traction_slip": report.avg_traction_slip_severity,
        }

        for key, (lbl_value, lbl_count) in self.metric_labels.items():
            sev = severity_map.get(key, 0.0)
            count = incident_counts.get(key, 0)
            lbl_value.setText(f"{sev:.0%}")
            lbl_count.setText(f"{count} incidentes")

        self.metrics_widget.show()

        # Pasar datos al panel de análisis
        self.analysis_panel.update_report(report)

        self.lbl_status.setText(
            f"✅  Análisis completado — {report.total_frames} frames, "
            f"{report.total_incidents} incidentes. Consultando a Ollama..."
        )

    def _on_recommendations_done(self, text: str):
        """Se llama cuando Ollama devuelve las recomendaciones."""
        self.recommendations_panel.update_recommendations(text)
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🔄  Analizar de nuevo")
        self.lbl_status.setText("✅  Recomendaciones listas. Revisa las pestañas Análisis y Recomendaciones.")

    def _on_error(self, message: str):
        """Se llama si ocurre cualquier error durante el análisis."""
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶  Analizar sesión")
        self.lbl_status.setText(f"❌  Error: {message}")


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def launch():
    """Lanza la aplicación Qt. Llamado desde main.py."""
    app = QApplication(sys.argv)
    app.setApplicationName("ACR Telemetry Advisor")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
