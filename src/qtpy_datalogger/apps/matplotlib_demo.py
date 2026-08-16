"""Embed matplotlib in ttk."""
# Reworked from https://github.com/matplotlib/matplotlib/blob/main/galleries/examples/user_interfaces/embedding_in_tk_sgskip.py

import asyncio
import logging
import pathlib
import tkinter as tk
from tkinter import font

import matplotlib.backend_bases as mpl_backend_bases
import numpy as np
import ttkbootstrap as ttk
from matplotlib.figure import Figure
from ttkbootstrap import constants as bootstyle

from qtpy_datalogger import guikit, ttkbootstrap_matplotlib

logger = logging.getLogger(pathlib.Path(__file__).stem)


class PlottingApp(guikit.AsyncWindow):
    """Tkinter GUI demonstrating an interactive matplotlib graph."""

    def create_user_interface(self) -> None:  # noqa: PLR0915 -- allow long function to create the UI
        """Create the main window and connect event handlers."""
        self.root_window.title("Embed Matplotlib in ttk")
        self.root_window.minsize(width=870, height=600)
        self.root_window.columnconfigure(0, weight=1)
        self.root_window.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root_window, name="main_frame", padding=16)
        main.grid(column=0, row=0, sticky=tk.NSEW)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=0)
        main.rowconfigure(1, weight=0)
        main.rowconfigure(2, weight=1)
        main.rowconfigure(3, weight=0)
        main.rowconfigure(4, weight=0)
        main.rowconfigure(5, weight=0)

        title_font = font.Font(weight="bold", size=16)
        title_label = ttk.Label(main, text="Matplotlib styled with ttkbootstrap", font=title_font)
        title_label.grid(column=0, row=0)

        slider_frame = ttk.Frame(main, name="slider_frame")
        slider_frame.grid(column=0, row=1, sticky=tk.N, pady=(16, 2))
        slider_frame.columnconfigure(0, weight=0)
        slider_frame.columnconfigure(1, weight=0)
        slider_frame.columnconfigure(2, weight=0)
        slider_frame.columnconfigure(3, weight=0)
        slider_frame.columnconfigure(4, weight=0)

        slider_label = ttk.Label(slider_frame, text="Frequency (f)")
        slider_label.grid(column=0, row=0, padx=(0, 4))

        slider_update = ttk.Scale(
            slider_frame,
            from_=0.001,
            to=0.01,
            value=0.005,
            orient=tk.HORIZONTAL,
            command=self.update_frequency,
        )
        slider_update.grid(column=1, row=0, padx=(4, 0))

        separator = ttk.Frame(slider_frame, style=bootstyle.PRIMARY, width=2, height=24)
        separator.grid(column=2, row=0, padx=(40, 32))

        combobox_label = ttk.Label(slider_frame, text="Theme")
        combobox_label.grid(column=3, row=0, sticky=tk.W, padx=(0, 4))

        self.theme_combobox = guikit.create_theme_combobox(slider_frame)
        self.theme_combobox.grid(column=4, row=0, sticky=tk.W, padx=(4, 0))

        canvas_frame = ttk.Frame(main, name="canvas_frame")
        canvas_frame.grid(column=0, row=2, sticky=tk.NSEW)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        figure_aspect = (4, 3)
        figure_dpi = 100
        mpl_figure = Figure(figsize=figure_aspect, dpi=figure_dpi)
        self.axes = mpl_figure.add_subplot()
        self.axes.set_title("Function plot")
        self.time_axis_label = self.axes.set_xlabel("time (s)", picker=True)  # Enable picking to generate mouse events
        self.y_axis_label = self.axes.set_ylabel("y", picker=True)  # Enable picking to generate mouse events
        self.axes.grid(
            visible=True,
            which="major",
            axis="y",
            dashes=(3, 8),
            zorder=-1,
        )
        self.t = np.arange(0, 1200, 0.1)
        (self.line,) = self.axes.plot(
            self.t,
            1000 * np.sin(2 * np.pi * self.t * float(slider_update.get())),
            label="y = 1000*sin(2*pi * f * t)",
        )
        self.axes.legend(
            title="Function",
            loc="upper left",
            draggable=True,
        )

        self.axis_tool_window = None
        self.background_tasks: set[asyncio.Task[object]] = set()
        self.canvas = ttkbootstrap_matplotlib.create_styled_plot_canvas(mpl_figure, canvas_frame)
        self.canvas.mpl_connect("key_press_event", mpl_backend_bases.key_press_handler)
        self.canvas.mpl_connect("button_press_event", self.on_graph_mouse_down)
        self.canvas.mpl_connect("pick_event", self.on_graph_pick)

        toolbar_row = ttk.Frame(main, name="toolbar_row")
        toolbar_row.grid(column=0, row=3, padx=(40, 80), sticky=tk.EW)
        toolbar_row.columnconfigure(0, weight=1)
        toolbar_row.columnconfigure(1, weight=0)

        side_spacer = ttk.Frame(toolbar_row, name="side_spacer")
        side_spacer.grid(column=0, row=0, sticky=tk.NSEW)

        toolbar_frame = ttkbootstrap_matplotlib.create_styled_plot_toolbar(toolbar_row, self.canvas)
        toolbar_frame.grid(column=1, row=0, sticky=tk.EW)

        theme_key = "cosmo-light"
        guikit.ThemeChanger.use_bootstrap_theme(theme_key, self.root_window)

    async def on_loop(self) -> None:
        """Update the window with new information."""
        await asyncio.sleep(1e-6)

    async def on_closing(self) -> None:
        """Finalize the window after exiting main loop."""

    def update_frequency(self, new_val: str) -> None:
        """Refresh the graph using the new user input."""
        f = float(new_val)
        y = 1000 * np.sin(2 * np.pi * f * self.t)
        self.line.set_data(self.t, y)
        self.canvas.draw()

    def on_graph_mouse_down(self, event_args: mpl_backend_bases.Event) -> None:
        """Handle mouse-down events from the graph."""
        if type(event_args) is not mpl_backend_bases.MouseEvent:
            return
        if not guikit.is_left_double_click(event_args):
            return

        clicked = event_args.inaxes
        if clicked is not self.axes:
            return

        if not self.axis_tool_window:
            self.axis_tool_window = guikit.AxisToolDialog(self.root_window)
            open_tool_window_task = asyncio.create_task(self.axis_tool_window.show(guikit.DialogBehavior.Modeless))
            self.background_tasks.add(open_tool_window_task)
            open_tool_window_task.add_done_callback(self.finalize_tool_window)
        limits = guikit.Range.create_infinite()
        self.axis_tool_window.attach_to_axis(
            event_args.canvas.draw_idle, self.axes, guikit.AxisToolDialog.Axis.Y, limits
        )

    def on_graph_pick(self, event_args: mpl_backend_bases.Event) -> None:
        """Handle pick events from the graph."""
        if type(event_args) is not mpl_backend_bases.PickEvent:
            return
        if not guikit.is_left_double_click(event_args.mouseevent):
            return

        clicked = event_args.artist
        if clicked is self.y_axis_label:
            axis = guikit.AxisToolDialog.Axis.Y
        elif clicked is self.time_axis_label:
            axis = guikit.AxisToolDialog.Axis.X
        else:
            return

        if not self.axis_tool_window:
            self.axis_tool_window = guikit.AxisToolDialog(self.root_window)
            open_tool_window_task = asyncio.create_task(self.axis_tool_window.show(guikit.DialogBehavior.Modeless))
            self.background_tasks.add(open_tool_window_task)
            open_tool_window_task.add_done_callback(self.finalize_tool_window)
        limits = guikit.Range.create_infinite()
        self.axis_tool_window.attach_to_axis(event_args.canvas.draw_idle, self.axes, axis, limits)

    def finalize_tool_window(self, task: asyncio.Task[object]) -> None:
        """Finalize the AxisToolDialog after the user closes it."""
        self.axis_tool_window = None
        self.background_tasks.discard(task)


if __name__ == "__main__":
    logger.debug(f"Launching {__package__}")
    asyncio.run(guikit.AsyncApp.create_and_run(PlottingApp))
