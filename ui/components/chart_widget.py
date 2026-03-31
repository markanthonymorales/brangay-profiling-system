import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Callable
from ui.theme import BG_COLOR, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, FONT_FAMILY


# Matplotlib style defaults
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#E0E0E0",
    "axes.grid": True,
    "grid.color": "#F0F0F0",
    "grid.linewidth": 0.5,
    "xtick.color": "#666666",
    "ytick.color": "#666666",
    "axes.labelcolor": "#444444",
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
})


class ChartWidget(ctk.CTkFrame):
    def __init__(self, master, figsize=(6, 4), **kwargs):
        super().__init__(master, fg_color=CARD_BG, corner_radius=12, **kwargs)
        self._figsize = figsize
        self._canvas = None
        self._figure = None

    def update_chart(self, draw_func: Callable[[Figure, any], None]):
        self.clear()

        self._figure = Figure(figsize=self._figsize, dpi=100, facecolor="#FFFFFF")
        self._figure.subplots_adjust(left=0.12, right=0.95, top=0.9, bottom=0.15)
        ax = self._figure.add_subplot(111)

        draw_func(self._figure, ax)

        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        canvas_widget = self._canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
        self._canvas.draw()

    def update_chart_multi(self, draw_func: Callable[[Figure], None]):
        """For charts needing multiple subplots — draw_func receives only the figure."""
        self.clear()

        self._figure = Figure(figsize=self._figsize, dpi=100, facecolor="#FFFFFF")
        self._figure.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.12, hspace=0.4)

        draw_func(self._figure)

        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        canvas_widget = self._canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
        self._canvas.draw()

    def clear(self):
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
            self._canvas = None
        if self._figure:
            plt.close(self._figure)
            self._figure = None

    def destroy(self):
        self.clear()
        super().destroy()
