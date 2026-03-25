"""
panel_recommendations.py
------------------------
Pantalla de recomendaciones de setup — Fase 6 del proyecto.

Muestra el texto generado por Ollama con formato visual limpio.
Permite copiar las recomendaciones al portapapeles.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QClipboard, QGuiApplication


class RecommendationsPanel(QWidget):
    """
    Panel que muestra las recomendaciones de setup generadas por el LLM.

    Se actualiza llamando a update_recommendations(text) desde MainWindow.
    """

    def __init__(self):
        super().__init__()
        self._build_ui()

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        """Construye el layout del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        # Cabecera con título y botón de copiar
        header_layout = QHBoxLayout()

        lbl = QLabel("Recomendaciones de Setup")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(lbl)

        header_layout.addStretch()

        self.btn_copy = QPushButton("📋  Copiar")
        self.btn_copy.setFixedWidth(120)
        self.btn_copy.setFixedHeight(36)
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        header_layout.addWidget(self.btn_copy)

        layout.addLayout(header_layout)

        # Info sobre el modelo usado
        self.lbl_model = QLabel("Modelo: llama3.1:8b (local via Ollama)")
        self.lbl_model.setStyleSheet("color: #555577; font-size: 11px;")
        layout.addWidget(self.lbl_model)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2a2a4e;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Mensaje mientras no hay datos
        self.lbl_empty = QLabel(
            "Las recomendaciones aparecerán aquí una vez que\n"
            "completes el análisis desde el Panel de Sesión."
        )
        self.lbl_empty.setStyleSheet("color: #888888; font-size: 13px;")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_empty)

        # Área de texto con las recomendaciones (oculta hasta tener datos)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.hide()
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #2a2a4e;
                border-radius: 8px;
                padding: 16px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        self.text_area.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.text_area)

        # Aviso legal / disclaimer
        self.lbl_disclaimer = QLabel(
            "⚠  Las recomendaciones son sugerencias generadas por IA. "
            "Valídalas siempre con tu criterio como piloto."
        )
        self.lbl_disclaimer.setStyleSheet("color: #555577; font-size: 11px;")
        self.lbl_disclaimer.setWordWrap(True)
        self.lbl_disclaimer.hide()
        layout.addWidget(self.lbl_disclaimer)

    # ── Actualización de datos ────────────────────────────────────────────────

    def update_recommendations(self, text: str):
        """
        Recibe el texto generado por Ollama y lo muestra en el panel.

        Parámetros
        ----------
        text : str
            Recomendaciones en lenguaje natural devueltas por SetupAdvisor.
        """
        self.lbl_empty.hide()
        self.text_area.setPlainText(text)
        self.text_area.show()
        self.lbl_disclaimer.show()
        self.btn_copy.setEnabled(True)

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        """Copia el texto de las recomendaciones al portapapeles."""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.text_area.toPlainText())

        # Feedback visual temporal en el botón
        self.btn_copy.setText("✅  Copiado")
        self.btn_copy.setEnabled(False)
        # Restaurar el botón después de 2 segundos
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self._restore_copy_button)

    def _restore_copy_button(self):
        """Restaura el texto del botón de copiar."""
        self.btn_copy.setText("📋  Copiar")
        self.btn_copy.setEnabled(True)

