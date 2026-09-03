"""Functions for applying ttkbootstrap styling to matplotlib visuals."""

import functools
import logging
import tkinter as tk
from enum import StrEnum
from tkinter import font

import ttkbootstrap as ttk
import ttkbootstrap.utils as ttk_utils
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from ttkbootstrap import constants as bootstyle

import qtpy_datalogger.guikit as gk

logger = logging.getLogger(__name__)


class ReservedName(StrEnum):
    """Reserved names used to implement matplotlib styling."""

    EmbeddedFigure = "mpl_figure_canvas"
    ToolbarBorder = "toolbar_border"


palette_color_key = {
    "background": bootstyle.LIGHT,  # The buttons in the toolbar only re-color themselves on creation, so force a light background color for all themes
    "foreground": bootstyle.DARK,  # Likewise, force a dark foreground color in text labels for all themes so that the (x, y) indicator remains readable
    "selectcolor": bootstyle.PRIMARY,
    "xtra_window_bg": "bg",  # bootstyle themes define "bg" but the library's constants omit them
    "xtra_window_fg": "fg",  # bootstyle themes define "fg" but the library's constants omit them
}


def create_styled_plot_canvas(
    figure: Figure,
    canvas_frame: ttk.Frame,
) -> FigureCanvasTkAgg:
    """Return a FigureCanvasTkAgg from matplotlib that responds to guikit.ThemeChanger.Event.BootstrapThemeChanged."""
    canvas = FigureCanvasTkAgg(figure, canvas_frame)
    canvas_widget = canvas.get_tk_widget()
    setattr(canvas_widget, ReservedName.EmbeddedFigure, canvas)
    canvas_widget.grid(column=0, row=0, sticky=tk.NSEW)
    gk.ThemeChanger.add_handler(canvas_frame, functools.partial(handle_theme_changed, canvas_widget))
    return canvas


def create_styled_plot_toolbar(
    parent: tk.BaseWidget,
    matching_canvas: FigureCanvasTkAgg,
    padleft: int = 10,
    toolbar_width: int = 500,
    border_thickness: int = 3,
) -> tk.Frame:
    """Return a tk.Frame that contains a NavigationToolbar from matplotlib and responds to guikit.ThemeChanger.Event.BootstrapThemeChanged."""
    canvas_aspect = matching_canvas.get_width_height()
    toolbar_width = max(toolbar_width, canvas_aspect[0])  # Any narrower and the updates flicker
    toolbar_height = 50  # Any shorter and the updates flicker
    final_width = padleft + toolbar_width + (2 * border_thickness)
    final_height = toolbar_height + (2 * border_thickness)

    toolbar_border = tk.Frame(parent, name=ReservedName.ToolbarBorder, width=final_width, height=final_height)
    toolbar_border.columnconfigure(0, weight=0, minsize=final_width)
    toolbar_border.rowconfigure(0, weight=0, minsize=final_height)
    toolbar_border.grid_propagate(False)  # Lock the height and width by ignoring child size requests
    gk.ThemeChanger.add_handler(toolbar_border, functools.partial(handle_theme_changed, toolbar_border))

    toolbar_frame = tk.Frame(toolbar_border, name="toolbar_frame")
    toolbar_frame.grid(column=0, row=0)
    toolbar_frame.columnconfigure(0, weight=1)
    toolbar_frame.columnconfigure(1, weight=1)
    toolbar_frame.rowconfigure(0, weight=0)

    left_side_padding = tk.Frame(toolbar_frame, name="left_side_padding", width=padleft, height=toolbar_height)
    left_side_padding.grid(column=0, row=0, sticky=tk.EW)

    toolbar_constraint = tk.Frame(toolbar_frame, name="toolbar_constraint", width=toolbar_width)
    toolbar_constraint.grid(column=1, row=0)

    # Place the toolbar in the same cell, covering its constraint
    toolbar = NavigationToolbar2Tk(
        matching_canvas,
        toolbar_frame,
        pack_toolbar=False,  # Use pack_toolbar=False for explicit placement
    )
    toolbar.grid(column=1, row=0, sticky=tk.NSEW)

    return toolbar_border


def handle_theme_changed(themed_widget: tk.Misc, event_args: tk.Event) -> None:
    """Handle the virtual event ThemeChanger.Event.BootstrapThemeChanged."""
    color_palette = gk.ThemeCatalog.get_instance().active_palette
    if isinstance(themed_widget, tk.Canvas):
        apply_figure_style(themed_widget, color_palette)
    elif isinstance(themed_widget, tk.Frame):
        apply_toolbar_style(themed_widget, color_palette)
    else:
        raise TypeError(type(themed_widget))


def apply_figure_style(canvas: tk.Canvas, color_palette: gk.ColorPalette) -> None:
    """Apply the specified theme to the specified matplotlib figure canvas."""
    mpl_figure_canvas = getattr(canvas, ReservedName.EmbeddedFigure, None)
    if not mpl_figure_canvas:
        # Nothing to style
        return

    fill_color = color_palette[palette_color_key["xtra_window_bg"]]
    plot_area_color = color_palette[palette_color_key["background"]]
    text_color = color_palette[palette_color_key["xtra_window_fg"]]

    figure = mpl_figure_canvas.figure
    if not isinstance(figure, Figure):
        raise TypeError(type(figure), Figure)
    figure.set_facecolor(fill_color)

    all_axes: list[Axes] = figure.axes
    for ax in all_axes:
        ax.set_title(
            ax.get_title(),
            color=text_color,
        )
        ax.set_facecolor(plot_area_color)
        for spine in ax.spines.values():
            spine.set_color(text_color)
            spine.set_linewidth(2)
        ax.tick_params(
            color=text_color,
            labelcolor=text_color,
            grid_color=text_color,
        )
        ax.set_xlabel(
            ax.get_xlabel(),
            color=text_color,
        )
        ax.set_ylabel(
            ax.get_ylabel(),
            color=text_color,
        )
        legend = ax.get_legend()
        if not legend:
            continue
        apply_legend_style(legend, color_palette)
    mpl_figure_canvas.draw()


def apply_legend_style(mpl_legend: Legend, color_palette: gk.ColorPalette) -> None:
    """Apply the specified theme to the matplotlib Legend."""
    fill_color = color_palette[palette_color_key["xtra_window_bg"]]
    text_color = color_palette[palette_color_key["xtra_window_fg"]]

    legend_frame = mpl_legend.get_frame()
    legend_frame.set_alpha(0.9)
    legend_frame.set_facecolor(fill_color)
    legend_frame.set_edgecolor(text_color)

    legend_title = mpl_legend.get_title()
    legend_title.set_color(text_color)

    legend_labels = mpl_legend.get_texts()
    for plot_label in legend_labels:
        plot_label.set_color(text_color)

    legend_lines = mpl_legend.get_lines()
    for index, plot_line in enumerate(legend_lines):
        if not plot_line.axes:
            continue
        owning_plot = plot_line.axes.lines[index]
        plot_line.set_color(owning_plot.get_color())


def apply_toolbar_style(tk_widget: tk.Widget, color_palette: gk.ColorPalette) -> None:
    """Apply the specified theme to the specified tk.Frame."""
    style_tree(tk_widget, color_palette)


def style_tree(widget: tk.Widget, color_palette: gk.ColorPalette) -> None:
    """Style the specified tk.Widget and its children."""
    if isinstance(widget, tk.Frame):
        style_frame(widget, color_palette)
    elif isinstance(widget, tk.Label):
        style_label(widget, color_palette)
    elif isinstance(widget, tk.Button):
        style_button(widget, color_palette)
    elif isinstance(widget, tk.Checkbutton):
        style_checkbutton(widget, color_palette)
    else:
        raise TypeError(type(widget))

    if widget.children:
        for child in widget.children.values():
            style_tree(child, color_palette)


def style_frame(frame: tk.Frame, color_palette: gk.ColorPalette) -> None:
    """Style a tk.Frame using the specified colors."""
    frame_color = color_palette[palette_color_key["background"]]
    if frame.winfo_name() == ReservedName.ToolbarBorder:
        frame_color = color_palette[palette_color_key["xtra_window_fg"]]
    frame.configure(
        {
            "background": frame_color,
        }
    )


def style_label(label: tk.Label, color_palette: gk.ColorPalette) -> None:
    """Style a tk.Label using the specified colors."""
    label.configure(
        {
            "background": color_palette[palette_color_key["background"]],
            "foreground": color_palette[palette_color_key["foreground"]],
            "font": font.Font(weight="bold"),
        }
    )


def style_button(button: tk.Button, color_palette: gk.ColorPalette) -> None:
    """Style a tk.Button using the specified colors."""
    press_color = change_color_luminance(color_palette[palette_color_key["background"]], -20)
    button.configure(
        {
            "background": color_palette[palette_color_key["background"]],
            "activebackground": press_color,  # Mouse down
        }
    )


def style_checkbutton(checkbutton: tk.Checkbutton, color_palette: gk.ColorPalette) -> None:
    """Style a tk.Checkbutton using the specified colors."""
    press_color = change_color_luminance(color_palette[palette_color_key["background"]], -20)
    checkbutton.configure(
        {
            "background": color_palette[palette_color_key["background"]],
            "activebackground": press_color,  # Mouse down
            "selectcolor": color_palette[palette_color_key["selectcolor"]],  # Active selection
        }
    )


def change_color_luminance(original_color: str, delta: int) -> str:
    """Return a new hex color code that represents the same color with a changed brightness."""
    as_hsl = ttk_utils.color_to_hsl(original_color, model="hex")
    new_luminance = as_hsl[-1] + delta
    new_color = ttk_utils.update_hsl_value(
        original_color,
        lum=new_luminance,
        inmodel="hex",
        outmodel="hex",
    )
    if not isinstance(new_color, str):
        raise TypeError(type(new_color), str)
    return new_color
