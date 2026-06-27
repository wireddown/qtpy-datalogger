"""Shared classes and helpers for creating GUIs."""

import asyncio
import enum
import functools
import json
import logging
import pathlib
import subprocess
import sys
import tkinter as tk
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import font
from typing import Any, ClassVar, NamedTuple

import click
import matplotlib.axes as mpl_axes
import matplotlib.backend_bases as mpl_backend_bases
import ttkbootstrap as ttk
import ttkbootstrap.icons as ttk_icons
import ttkbootstrap.style as ttk_style
import ttkbootstrap.themes.standard as ttk_themes
import ttkbootstrap.tooltip as ttk_tooltip
from tkfontawesome import icon_to_image
from ttkbootstrap import constants as bootstyle

from qtpy_datalogger import datatypes

logger = logging.getLogger(__name__)


class StyleKey(enum.StrEnum):
    """A class that extends the palette names of ttkbootstrap styles."""

    Fg = "fg"
    SelectFg = "selectfg"


class AsyncApp:
    """A Tk application wrapper that cooperates with asyncio."""

    @staticmethod
    async def create_and_run(async_window_type: type) -> None:
        """
        Create and run an AsyncWindow cooperatively with asyncio.

        Create a new instance of async_window_type within an asynchronous function so that
        the new instance can use the asyncio event loop. Creating one outside an
        asynchronous function prevents the new instance from using async code
        because asyncio has not created or started an event loop.

        The base type of async_window_type must be an AsyncWindow to use cooperative event handling.

        Example:
        asyncio.run(AsyncApp.create_and_run(AsyncWindowSubclass))

        """
        if not issubclass(async_window_type, AsyncWindow):
            raise TypeError()

        app = async_window_type()
        app.create_user_interface()
        app.root_window.update_idletasks()
        await app.show()


class DialogBehavior(enum.StrEnum):
    """
    Supported behaviors for AsyncDialogs.

    Modal:
    Prevent input to all other app windows until dismissed. Hide the maximize and minimize buttons and the icon in the Windows task bar.

    Modeless:
    Allow input to all other app windows. Hide the maximize and minimize buttons and the icon in the Windows task bar.

    Standalone:
    Allow input to all other app windows. Show the maximize and minimize buttons and the icon in the Windows task bar.

    All dialogs close when the the main parent window closes.
    """

    Modal = "Modal"
    Modeless = "Modeless"
    Standalone = "Standalone"


class AsyncDialog:
    """
    A Tk Toplevel wrapper that cooperates with asyncio.

    Define a subclass of AsyncDialog and override both create_user_interface() and
    async on_loop() to create a dialog with Tk that cooperates with asyncio APIs.

    Call show() to present the dialog and retrieve its result after it closes. To set
    the result, assign a value to self.result in on_loop() or on_closing().

    Override set_position() to place the dialog before presentation. Call exit() to
    close the dialog.

    Required overrides
    - create_user_interface(self)

    Remaining overrides
    - set_position(self)
    - async on_loop(self)
    - on_closing(self)

    Helper methods
    - self.exit()
    """

    _open_dialogs: ClassVar[set["AsyncDialog"]] = set()
    _open_dialog_tasks: ClassVar[set[asyncio.Task]] = set()

    @classmethod
    def show_no_wait(cls, dialog: "AsyncDialog", behavior: DialogBehavior) -> None:
        """Show the dialog without waiting for or returning a result."""
        if dialog not in cls._open_dialogs:

            def finalize_safe_show(task: asyncio.Task) -> None:
                cls._open_dialogs.discard(dialog)
                cls._open_dialog_tasks.discard(task)

            open_dialog_task = asyncio.create_task(dialog.show(behavior))
            open_dialog_task.add_done_callback(finalize_safe_show)
            cls._open_dialogs.add(dialog)
            cls._open_dialog_tasks.add(open_dialog_task)

    def __init__(self, parent: ttk.Toplevel | ttk.Window, title: str) -> None:
        """Initialize a new Tk Toplevel and cache the asyncio event loop."""
        self.parent = parent
        self.root_window = ttk.Toplevel(master=self.parent, title=title)
        self.root_window.withdraw()

        self.io_loop = asyncio.get_running_loop()
        self.should_run_loop = True

        def __on_closing(event: tk.Event | None = None) -> None:
            self.exit()

        self.root_window.protocol("WM_DELETE_WINDOW", __on_closing)
        self.root_window.bind("<Escape>", __on_closing)

        self.result = None
        self.initial_focus = self.root_window
        self.create_user_interface()
        self.root_window.update_idletasks()  # Calculate geometry and size information

    async def show(self, behavior: DialogBehavior) -> object | None:
        """Show the dialog and cooperatively run with asyncio."""
        if behavior != DialogBehavior.Standalone and self.parent.winfo_viewable():
            self.root_window.transient(self.parent)

        self.set_position()
        self.root_window.deiconify()  # Render and present
        self.initial_focus.focus_set()
        self.root_window.wait_visibility()
        self.root_window.update()

        if behavior == DialogBehavior.Modal:
            self.root_window.grab_set()

        while self.should_run_loop:
            await asyncio.sleep(0)
            await self.on_loop()
            self.root_window.update()

        self.on_closing()
        self.parent.focus_set()
        self.root_window.destroy()
        return self.result

    def set_position(self) -> None:
        """Set the dialog's position."""
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        x_pos = parent_x + 100
        y_pos = parent_y + 50
        self.root_window.geometry(f"+{x_pos}+{y_pos}")

    def create_user_interface(self) -> None:
        """Create the layout and widget event handlers."""

    async def on_loop(self) -> None:
        """Update dialog elements and poll asyncio resources."""

    def on_closing(self) -> None:
        """Finalize the dialog result after exiting the main loop."""

    def exit(self) -> None:
        """Close the dialog and exit."""
        self.should_run_loop = False


class AsyncWindow:
    """
    A Tk root window wrapper that cooperates with asyncio.

    Define a subclass of AsyncWindow and override both create_user_interface() and
    async on_loop() to create a GUI with Tk that cooperates with asyncio APIs.

    Required overrides
    - create_user_interface(self)

    Remaining overrides
    - on_show()
    - async on_loop(self)
    - on_closing(self)

    Helper methods
    - self.exit()

    Example:
    asyncio.run(AsyncApp.create_and_run(AsyncWindowSubclass))

    """

    def __init__(self) -> None:
        """Initialize a new Tk root and cache the asyncio event loop."""
        # Let subclasses set the window icon
        self.root_window = ttk.Window(iconphoto=None)
        self.root_window.withdraw()

        self.io_loop = asyncio.get_running_loop()
        self.should_run_loop = True

        def __on_closing() -> None:
            self.exit()

        self.root_window.protocol("WM_DELETE_WINDOW", __on_closing)

    async def show(self) -> None:
        """Show the window and cooperatively run with asyncio."""
        self.root_window.deiconify()
        self.root_window.wait_visibility()
        await self.on_showing()
        self.root_window.update()

        while self.should_run_loop:
            await asyncio.sleep(0)
            await self.on_loop()
            self.root_window.update()

        await self.on_closing()
        self.root_window.quit()

    def create_user_interface(self) -> None:
        """Create the layout and widget event handlers."""

    async def on_showing(self) -> None:
        """Initialize the window before entering main loop."""

    async def on_loop(self) -> None:
        """Update window elements and poll asyncio resources."""

    async def on_closing(self) -> None:
        """Finalize the window after exiting main loop."""

    def exit(self) -> None:
        """Close the window and exit."""
        self.should_run_loop = False


class ActionDialog(AsyncDialog):
    """A dialog that presents a message and handles user actions."""

    class Action(enum.StrEnum):
        """Supported actions for an ActionDialog."""

        NoAction = "NoAction"
        Cancel = "Cancel"
        CopyAll = "Copy all"
        Ok = "OK"

    class Information(NamedTuple):
        """A NamedTuple that holds information for a supported Action."""

        text: str
        command: Callable
        style: str

    def __init__(self, parent: ttk.Toplevel | ttk.Window) -> None:
        """Initialize a new ActionDialog instance."""
        self.action_information = self.build_action_information()
        super().__init__(parent, "")

    def build_action_information(self) -> dict[Action, Information]:
        """Create the action information for the dialog."""
        return {
            ActionDialog.Action.Ok: ActionDialog.Information(
                text="OK",
                command=self.exit,
                style=bootstyle.PRIMARY,
            ),
            ActionDialog.Action.CopyAll: ActionDialog.Information(
                text="Copy all",
                command=self.copy_message,
                style=bootstyle.OUTLINE,
            ),
            ActionDialog.Action.Cancel: ActionDialog.Information(
                text="Cancel",
                command=self.exit,
                style=(bootstyle.OUTLINE, bootstyle.WARNING),  # ty: ignore[invalid-argument-type] -- the type hint for ttk uses strings not tuples
            ),
        }

    def handle_ctrl_c(self, event_args: tk.Event) -> None:
        """Handle the Ctrl-C keyboard event."""
        self.copy_message()

    def copy_message(self) -> None:
        """Copy the full message to the clipboard."""
        message_paragraphs = self.message.split("\n\n")
        unwrapped_paragraphs = [paragraph.replace("\n", " ") for paragraph in message_paragraphs]
        unwrapped_message = "\n\n".join(unwrapped_paragraphs)
        self.parent.clipboard_clear()
        self.parent.clipboard_append(unwrapped_message)
        success_text = f"{ttk_icons.Emoji.get('white heavy check mark')}   Copied!"
        show_button_feedback(self.copy_button, command_result=True, success_text=success_text)

    def create_user_interface(self) -> None:
        """Create the layout and widget event handlers."""
        self.root_window.columnconfigure(0, weight=1)
        self.root_window.rowconfigure(0, weight=1)
        self.root_window.resizable(width=False, height=False)

        main_frame = ttk.Frame(self.root_window, padding=16)
        main_frame.grid(column=0, row=0, sticky=tk.NSEW)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1, minsize=8)  # Filler
        main_frame.rowconfigure(1, weight=1)  # Image and message frame
        main_frame.rowconfigure(2, weight=1, minsize=20)  # Filler
        main_frame.rowconfigure(3, weight=1)  # Button frame

        self.message_frame = ttk.Frame(main_frame)
        self.message_frame.columnconfigure(0, weight=1)  # Message image
        self.message_frame.columnconfigure(1, weight=1, minsize=200)  # Message text
        self.message_frame.grid(column=0, row=1)

        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.columnconfigure(0, weight=1)  # Filler
        self.button_frame.columnconfigure(1, weight=1)  # Action 3
        self.button_frame.columnconfigure(2, weight=1)  # Action 2
        self.button_frame.columnconfigure(3, weight=1)  # Action 1
        self.button_frame.grid(column=0, row=3, sticky=tk.E)

    def update(  # noqa PLR0913 -- allow many parameters for a framework class method
        self,
        title: str = "",
        image_name: str = "",
        image_fill: str = "",
        message_paragraphs: list[str] | None = None,
        action1: Action = Action.Ok,
        action2: Action = Action.CopyAll,
        action3: Action = Action.NoAction,
    ) -> None:
        """Update the UI with new information."""
        self.root_window.title(title)
        if not image_name:
            image_name = "o"
        if not image_fill:
            image_fill = StyleKey.Fg
        self.message_image = image_from_icon(name=image_name, fill=hex_string_for_style(image_fill), scale_to_height=40)
        if not message_paragraphs:
            message_paragraphs = ["Click OK to close."]
        self.message = "\n\n".join([click.wrap_text(message, width=64) for message in message_paragraphs])
        if action1 == ActionDialog.Action.NoAction:
            action1 = ActionDialog.Action.Ok
        self.action1 = action1
        self.action2 = action2
        self.action3 = action3

        for widget in [
            *self.message_frame.winfo_children(),
            *self.button_frame.winfo_children(),
        ]:
            widget.destroy()

        image_label = ttk.Label(self.message_frame, image=self.message_image, padding=4)
        image_label.grid(column=0, row=0, sticky=tk.N, padx=(12, 8), pady=(12, 0))
        image_text = ttk.Label(self.message_frame, text=self.message)
        image_text.grid(column=1, row=0, sticky=tk.W, padx=(8, 32), pady=(4, 0))

        for index, action in enumerate([self.action1, self.action2, self.action3]):
            if action == ActionDialog.Action.NoAction:
                continue
            button = ttk.Button(
                self.button_frame,
                command=self.action_information[action].command,
                text=self.action_information[action].text,
                style=self.action_information[action].style,
            )
            button.grid(column=3 - index, row=0, sticky=tk.E, padx=(8, 0))
            if index == 0:
                self.initial_focus = button
            if action == ActionDialog.Action.CopyAll:
                button.configure(width=12)
                self.copy_button = button
                self.root_window.bind("<Control-c>", self.handle_ctrl_c)

    async def on_loop(self) -> None:
        """Update UI elements."""
        await asyncio.sleep(20e-3)


class AboutDialog(AsyncDialog):
    """A class that presents information about the app."""

    def __init__(  # noqa PLR0913 -- allow many parameters for a framework class
        self,
        parent: ttk.Toplevel | ttk.Window,
        app_name: str = "",
        app_icon: str = "",
        all_icons: list[str] | None = None,
        help_url: str = "",
        source_url: str = "",
    ) -> None:
        """Initialize a new AboutDialog instance."""
        self.app_name = app_name
        if not app_icon:
            app_icon = "chart-line"
        if not all_icons:
            all_icons = ["microchip", "worm", app_icon]
        self.app_icons = all_icons[:3]
        self.icon_labels = []
        self.app_icon_images = []
        self.help_url = help_url or datatypes.Links.Help
        self.source_url = source_url or datatypes.Links.Source
        self.copy_version_text = "Copy version"
        super().__init__(parent, f"About {app_name}".strip())

    def create_user_interface(self) -> None:  # noqa: PLR0915 -- allow long function to create the UI
        """Create the UI for the AboutDialog."""
        self.root_window.columnconfigure(0, weight=1)
        self.root_window.rowconfigure(0, weight=1)
        self.root_window.resizable(width=False, height=False)
        main_frame = ttk.Frame(self.root_window, padding=16)
        main_frame.grid(column=0, row=0, sticky=tk.NSEW)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        message_frame = ttk.Frame(main_frame)
        message_frame.grid(column=0, row=0, sticky=tk.NSEW)
        message_frame.columnconfigure(0, weight=0, minsize=40)  # Filler
        message_frame.columnconfigure(1, weight=0)  # Icon1
        message_frame.columnconfigure(2, weight=0)  # Icon2
        message_frame.columnconfigure(3, weight=0)  # Icon3
        message_frame.columnconfigure(4, weight=0, minsize=20)  # Filler
        message_frame.columnconfigure(5, weight=0)  # Text
        message_frame.columnconfigure(6, weight=0, minsize=40)  # Filler
        message_frame.rowconfigure(0, weight=0, minsize=20)  # Filler
        message_frame.rowconfigure(1, weight=0)  # Icons and Name
        message_frame.rowconfigure(2, weight=0)  # Icons and Version
        message_frame.rowconfigure(3, weight=0)  # Separator
        message_frame.rowconfigure(4, weight=0)  # Help
        message_frame.rowconfigure(5, weight=0)  # Source
        message_frame.rowconfigure(6, weight=0)  # Source2
        message_frame.rowconfigure(7, weight=0, minsize=50)  # Filler

        for index, _ in enumerate(self.app_icons):
            icon_column = index + 1  # Column 0 is margin filler
            icon_label = ttk.Label(message_frame, padding=4)
            icon_label.grid(column=icon_column, row=1, rowspan=2)
            self.icon_labels.append(icon_label)

        self.refresh_icons()

        name_label = ttk.Label(message_frame, font=font.Font(weight="bold", size=28), text=self.app_name)
        name_label.grid(column=5, row=1, sticky=tk.W)
        self.notice_information = datatypes.SnsrNotice.get_package_notice_info(allow_dev_version=True)
        bullet = ttk_icons.Emoji.get("black medium small square")
        version_label = ttk.Label(
            message_frame,
            text=f"{self.notice_information.version} {bullet} {self.notice_information.timestamp:%Y-%m-%d} {bullet} {self.notice_information.commit}",
        )
        version_label.grid(column=5, row=2, sticky=tk.W, padx=(2, 0))
        separator = ttk.Separator(message_frame)
        separator.grid(column=1, row=3, columnspan=5, sticky=tk.EW, pady=4)
        button_text_color = hex_string_for_style(StyleKey.SelectFg)
        spacer = "   "
        self.help_icon = image_from_icon("parachute-box", fill=button_text_color, scale_to_width=16)
        help_button = ttk.Button(
            message_frame,
            compound=tk.LEFT,
            image=self.help_icon,
            text=f"{spacer}Online help ",  # The trailing space helps with internal margins
            style=bootstyle.INFO,
            width=18,
            command=functools.partial(webbrowser.open_new_tab, self.help_url),
        )
        help_button.grid(column=5, row=4, sticky=tk.W, pady=(18, 0))
        self.source_icon = image_from_icon("github-alt", fill=button_text_color, scale_to_width=16)
        source_button = ttk.Button(
            message_frame,
            compound=tk.LEFT,
            image=self.source_icon,
            text=f"{spacer}Source code",
            style=bootstyle.INFO,
            width=18,
            command=functools.partial(webbrowser.open_new_tab, self.source_url),
        )
        source_button.grid(column=5, row=5, sticky=tk.W, pady=(22, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(column=0, row=1, sticky=tk.NSEW, padx=(0, 16), pady=(8, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0)
        button_frame.rowconfigure(0, weight=0)
        self.copy_version_button = ttk.Button(
            button_frame,
            text=self.copy_version_text,
            style=bootstyle.OUTLINE,
            command=self.copy_version,
            width=12,
        )
        self.copy_version_button.grid(column=0, row=0, sticky=tk.E, padx=(0, 16))
        ok_button = ttk.Button(button_frame, text="OK", command=self.exit)
        ok_button.grid(column=1, row=0, sticky=tk.E)
        self.initial_focus = ok_button

        ThemeChanger.add_handler(self.root_window, self.on_theme_changed)

    def refresh_icons(self) -> None:
        """Refresh the icons in the dialog using the active style."""
        icon_height = 48
        icon_color = hex_string_for_style(StyleKey.Fg)
        self.app_icon_images.clear()
        for icon_name, icon_label in zip(self.app_icons, self.icon_labels, strict=True):
            icon_image = image_from_icon(icon_name, fill=icon_color, scale_to_height=icon_height)
            self.app_icon_images.append(icon_image)
            icon_label.configure(image=icon_image)

    def copy_version(self) -> None:
        """Copy the version information to the clipboard."""
        formatted_version = {
            "version": self.notice_information.version,
            "timestamp": str(self.notice_information.timestamp),
            "commit": self.notice_information.commit,
        }
        self.parent.clipboard_clear()
        self.parent.clipboard_append(json.dumps(formatted_version))
        success_text = f"{ttk_icons.Emoji.get('white heavy check mark')}   Copied!"
        show_button_feedback(self.copy_version_button, command_result=True, success_text=success_text)

    async def on_loop(self) -> None:
        """Update UI elements."""
        await asyncio.sleep(20e-3)

    def on_theme_changed(self, event_args: tk.Event) -> None:
        """Handle the ThemeChanger.Event.BootstrapThemeChanged event."""
        self.refresh_icons()


@dataclass(order=True, frozen=True)
class Range:
    """A class that represents a numerical range."""

    lower: float
    """The lower bound of the range."""

    upper: float
    """The upper bound of the range."""

    @staticmethod
    def from_matplotlib(mpl_limits: tuple[float, float]) -> "Range":
        """Create a Range from the matplotlib representation."""
        return Range(lower=mpl_limits[0], upper=mpl_limits[1])

    @staticmethod
    def create_infinite() -> "Range":
        """Create a Range that spans Python's support for floating point values."""
        largest_float = sys.float_info.max
        return Range(lower=-1 * largest_float, upper=largest_float)


class AxisToolDialog(AsyncDialog):
    """A dialog that shows controls for configuring the attached matplotlib axis."""

    class Axis(enum.StrEnum):
        """Enumeration representing the dimension of the attached axis."""

        X = "X"
        Y = "Y"

    class AxisScale(enum.StrEnum):
        """Enumeration representing the numerical scale of the attached axis."""

        Linear = "Linear"
        Log = "Log"

    def __init__(self, parent: ttk.Toplevel | ttk.Window) -> None:
        """Initialize a new AxisToolDialog."""
        self.tool_frames: dict[str, ttk.Frame] = {}
        super().__init__(parent=parent, title="")

    async def on_loop(self) -> None:
        """Update UI elements."""
        await asyncio.sleep(20e-3)

    def attach_to_axis(self, refresh_graph: Callable[[], None], axes: mpl_axes.Axes, axis: Axis, limits: Range) -> None:
        """Present a UI that configures the specified axis."""
        self.root_window.title("Axis settings")
        self.root_window.columnconfigure(0, weight=1)
        self.root_window.rowconfigure(0, weight=1)
        self.root_window.minsize(width=170, height=166)
        self.root_window.maxsize(width=170, height=400)

        frame_key = f"{axes!r}.{axis}"
        if frame_key not in self.tool_frames:
            tool_frame = self.create_axis_tool_frame(refresh_graph, axes, axis, limits)
            self.tool_frames[frame_key] = tool_frame
        tool_frame = self.tool_frames[frame_key]

        # Raise the active tool_frame and remove the previous one
        tool_frame.grid(column=0, row=0, sticky=tk.NSEW)
        for child in self.root_window.children.values():
            if child is tool_frame:
                continue
            child.grid_forget()
        self.root_window.update_idletasks()  # Apply layout and compose visual tree
        self.root_window.focus()

    def create_axis_tool_frame(  # noqa: PLR0915 -- allow long function to create the UI
        self, refresh_graph: Callable[[], None], axes: mpl_axes.Axes, axis: Axis, limits: Range
    ) -> ttk.Frame:
        """Create a ttk.Frame that shows axis configuration settings and handles user input."""
        tool_frame = ttk.Frame(self.root_window, padding=16)
        tool_frame.columnconfigure(0, weight=1)  # Labels
        tool_frame.columnconfigure(1, weight=1)  # Controls
        tool_frame.rowconfigure(0, weight=0)  # Name of axis under edit
        tool_frame.rowconfigure(1, weight=0)  # Upper limit
        tool_frame.rowconfigure(2, weight=0)  # Lower limit
        tool_frame.rowconfigure(3, weight=1)  # Scale

        if axis == AxisToolDialog.Axis.X:
            plot_axis = axes.xaxis
            axis_view_limits = axes.get_xlim()
            axis_scale = axes.get_xscale()
            set_axis_limits = axes.set_xlim
            set_axis_scale = axes.set_xscale
        else:
            plot_axis = axes.yaxis
            axis_view_limits = axes.get_ylim()
            axis_scale = axes.get_yscale()
            set_axis_limits = axes.set_ylim
            set_axis_scale = axes.set_yscale

        axis_name = ttk.Label(
            tool_frame,
            text=plot_axis.get_label().get_text(),
            font=font.Font(family="Segoe UI", size=10, weight=font.BOLD),
        )
        axis_name.grid(column=0, columnspan=2, row=0, pady=(0, 8), sticky=tk.W)

        max_limit_label = ttk.Label(tool_frame, text="Maximum")
        max_limit_label.grid(column=0, row=1, padx=(0, 12), pady=(8, 8), sticky=tk.EW)
        min_limit_label = ttk.Label(tool_frame, text="Minimum")
        min_limit_label.grid(column=0, row=2, padx=(0, 12), pady=(8, 8), sticky=tk.EW)
        scale_label = ttk.Label(tool_frame, text="Scale")
        scale_label.grid(column=0, row=3, padx=(0, 12), pady=(8, 8), sticky=(tk.EW, tk.N))

        viewing_range = Range.from_matplotlib(axis_view_limits)

        axis_max_input = NumericInput(tool_frame, limits=limits, default_value=viewing_range.upper)
        ttk_tooltip.ToolTip(
            axis_max_input.widget, text=f"Cannot be greater than {limits.upper}", bootstyle=bootstyle.DEFAULT
        )
        axis_max_input.widget.grid(column=1, row=1, sticky=tk.EW)

        axis_min_input = NumericInput(tool_frame, limits=limits, default_value=viewing_range.lower)
        ttk_tooltip.ToolTip(
            axis_min_input.widget, text=f"Cannot be less than {limits.lower}", bootstyle=bootstyle.DEFAULT
        )
        axis_min_input.widget.grid(column=1, row=2, sticky=tk.EW)

        def on_new_upper_or_lower_bound(event_args: tk.Event) -> None:
            """Handle the ValueChanged event for the NumericInput control."""
            lower_bound = axis_min_input.value
            upper_bound = axis_max_input.value
            set_axis_limits(lower_bound, upper_bound)
            refresh_graph()

        axis_max_input.widget.bind(NumericInput.Event.ValueChanged, on_new_upper_or_lower_bound)
        axis_min_input.widget.bind(NumericInput.Event.ValueChanged, on_new_upper_or_lower_bound)

        def handle_scale_selection(new_selection: str) -> None:
            """Handle the selection event for the linear/log scale combobox."""
            if new_selection == axis_scale:
                return
            if new_selection == AxisToolDialog.AxisScale.Log:
                lower_view_limit = axis_view_limits[0]
                safe_minimum = max(0.01, lower_view_limit)
                set_axis_limits(safe_minimum, axis_max_input.value)  # Change limits to update scale
                axis_min_input._value = safe_minimum
                axis_min_input.widget.configure(state=tk.DISABLED)
                set_axis_scale(new_selection.lower())
            else:
                previous_value = float(axis_min_input.widget.get())
                set_axis_scale(new_selection.lower())  # Change scale to update limits
                set_axis_limits(previous_value, axis_max_input.value)
                axis_min_input._value = previous_value
                axis_min_input.widget.configure(state=tk.NORMAL)
            refresh_graph()

        scale_input = create_dropdown_combobox(
            parent=tool_frame,
            values=[AxisToolDialog.AxisScale.Linear, AxisToolDialog.AxisScale.Log],
            width=5,
            justify=bootstyle.RIGHT,
            completion=handle_scale_selection,
        )
        scale_input.grid(column=1, row=3, sticky=(tk.EW, tk.N))
        scale_input.set(axis_scale.capitalize())

        return tool_frame


class NumericInput:
    """A wrapped ttk.Spinbox that coerces text input into a numeric value."""

    class Event(enum.StrEnum):
        """Events emitted by this control."""

        ValueChanged = "<<ValueChanged>>"

    def __init__(self, parent: tk.Widget, limits: Range, default_value: float) -> None:
        """Initialize a new NumericInput widget."""
        decimal_places_for_max = {
            100: 0,
            10: 1,
            1: 2,
        }
        increment_for_max = {
            100: 10.0,
            20: 1.0,
            2: 0.1,
        }
        largest_magnitude = max(abs(limits.upper), abs(limits.lower))
        decimal_places = get_first_in_range(largest_magnitude, decimal_places_for_max)
        increment = get_first_in_range(largest_magnitude, increment_for_max)

        self._value = default_value
        self._input_variable = tk.StringVar(value=f"{default_value:.{decimal_places}f}")
        self._input_control = ttk.Spinbox(
            master=parent,
            from_=limits.lower,
            to=limits.upper,
            increment=increment,
            format=f"%.{decimal_places}f",
            width=5,
            justify=tk.RIGHT,
            textvariable=self._input_variable,
        )

        # Configure the input-validation and entry-complete pipeline
        def value_is_indeterminate(candidate_value: str) -> bool:
            """Return True if the value is not a fully formed floating point number."""
            # Allow empty and minus sign to support keyboard entry
            return len(candidate_value) == 0 or candidate_value == "-"

        def try_as_float(string_value: str) -> float | None:
            """If string_value is a float, return its value as a float. Otherwise return None."""
            try:
                as_float = float(string_value)
            except ValueError:
                return None
            else:
                return as_float

        def check_float_in_range(sender: ttk.Spinbox, limits: Range, candidate_value: str) -> bool:
            """Return True if candidate_value is a float and in range."""
            if value_is_indeterminate(candidate_value):
                return True

            as_float = try_as_float(candidate_value)
            if as_float is None:
                return False

            is_valid = limits.lower <= as_float <= limits.upper
            new_style = bootstyle.DEFAULT if is_valid else bootstyle.DANGER
            sender.configure(bootstyle=new_style)
            return is_valid

        def handle_new_value(sender: ttk.Spinbox, variable_name: str, empty: str, operation: str) -> None:
            """Process a new value that passed input validation."""
            new_value = sender.get()
            if value_is_indeterminate(new_value):
                return
            as_float = float(new_value)
            self._value = as_float

        def handle_entry_complete(event_args: tk.Event) -> None:
            """Handle the Enter key and FocusOut events."""
            sender = event_args.widget
            if not isinstance(sender, ttk.Spinbox):
                raise TypeError()
            sender.icursor(tk.END)

            # Widget events like MouseWheel fire before the widget receives the new value
            # Allow the trace subroutine to execute and set the new value
            # Otherwise subscribed event handlers see the widget with the previous value
            sender.after(0, sender.selection_clear)
            sender.after(0, self._input_control.event_generate, NumericInput.Event.ValueChanged)

        # Validate keyboard input for floats
        # https://www.tcl-lang.org/man/tcl8.6/TkCmd/ttk_entry.htm#M34
        # - Validate all user actions: key input, focus-in, focus-out
        # - %P: incoming new value to be validated
        input_validator = parent.register(functools.partial(check_float_in_range, self._input_control, limits))
        self._input_control.configure(validate=tk.ALL, validatecommand=(input_validator, "%P"))
        # Once valid, run a follow-up trace command to accept the new float
        self._input_variable.trace_add("write", functools.partial(handle_new_value, self._input_control))
        # Once a user action commits the new value, emit the value changed event
        self._input_control.bind("<<Increment>>", handle_entry_complete)
        self._input_control.bind("<<Decrement>>", handle_entry_complete)
        self._input_control.bind("<MouseWheel>", handle_entry_complete)
        self._input_control.bind("<KeyPress-Return>", handle_entry_complete)
        self._input_control.bind("<FocusOut>", handle_entry_complete)

    @property
    def widget(self) -> ttk.Spinbox:
        """Return the Tk widget for this NumericInput."""
        return self._input_control

    @property
    def value(self) -> float:
        """Return the value of the NumericInput as a float."""
        return self._value


class ThemeChanger:
    """A class that changes Tk themes and emits a corresponding event."""

    class Event(enum.StrEnum):
        """An enumeration of events emitted by this class."""

        BootstrapThemeChanged = "<<BootstrapThemeChanged>>"

    @staticmethod
    def add_handler(owner: tk.Misc, command: Callable[[tk.Event], None]) -> str:
        """Subscribe command as a handler for the BootstrapThemeChanged event and return a unique ID for the binding."""
        # **Must** bind to the application, emit to the root window, add to the handler list
        # - See https://stackoverflow.com/a/31798918
        return owner.winfo_toplevel().bind_all(ThemeChanger.Event.BootstrapThemeChanged, command, add="+")

    @staticmethod
    def use_bootstrap_theme(new_theme: str, owner: tk.Misc) -> None:
        """Change the ttkbootstrap theme and notify BootstrapThemeChanged subscribers."""
        ttk.Style().theme_use(new_theme)
        owner.winfo_toplevel().event_generate(ThemeChanger.Event.BootstrapThemeChanged)


class DemoWithAnimation(AsyncWindow):
    """Compare synchronous vs asynchronous calls in Tk."""

    def __init__(self) -> None:
        """Call the parent initializer."""
        super().__init__()

    def create_user_interface(self) -> None:
        """Create text label to animate and define buttons to demonstrate blocking vs async calls."""
        self.root_window.title("Async Demo")
        icon = tk.PhotoImage(master=self.root_window, data=ttk_icons.Icon.info)
        self.root_window.iconphoto(True, icon)

        self.animation = "🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🩶🖤"
        main_frame, self.label, self.progressbar = create_demo_ui(self.root_window, self.io_loop)

        modal_button = ttk.Button(
            main_frame,
            text="Modal",
            command=functools.partial(self.open_dialog, DialogBehavior.Modal),
            style=(bootstyle.SECONDARY, bootstyle.INFO),  # ty: ignore[invalid-argument-type] -- the type hint for ttk uses strings not tuples
        )
        modal_button.grid(column=0, row=3, sticky=tk.EW, padx=8)

        modeless_button = ttk.Button(
            main_frame,
            text="Modeless",
            command=functools.partial(self.open_dialog, DialogBehavior.Modeless),
            style=(bootstyle.SECONDARY, bootstyle.INFO),  # ty: ignore[invalid-argument-type] -- the type hint for ttk uses strings not tuples
        )
        modeless_button.grid(column=1, row=3, sticky=tk.EW, pady=8)

        standalone_button = ttk.Button(
            main_frame,
            text="Standalone",
            command=functools.partial(self.open_dialog, DialogBehavior.Standalone),
            style=bootstyle.SECONDARY,
        )
        standalone_button.grid(column=2, row=3, sticky=tk.EW, padx=8)

    async def on_loop(self) -> None:
        """Update the animation."""
        self.label["text"] = self.animation
        self.animation = self.animation[-1] + self.animation[0:-1]
        await asyncio.sleep(0.06)

    def open_dialog(self, behavior: DialogBehavior) -> None:
        """Open an AsyncDialog using the specified Behavior."""
        dialog = DialogWithAnimation(self.root_window, title=f"{behavior} dialog")
        self.io_loop.create_task(dialog.show(behavior))


class DialogWithAnimation(AsyncDialog):
    """Host synchronous and asynchronous calls in a dialog."""

    def __init__(self, parent: ttk.Toplevel | ttk.Window, title: str) -> None:
        """Call the parent initializer."""
        super().__init__(parent, title)

    def create_user_interface(self) -> None:
        """Create text label to animate and define buttons to demonstrate blocking vs async calls."""
        self.animation = "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬜⬜"
        _, self.label, self.progressbar = create_demo_ui(self.root_window, self.io_loop)

    async def on_loop(self) -> None:
        """Update the animation."""
        self.label["text"] = self.animation
        self.animation = self.animation[-1] + self.animation[0:-1]
        await asyncio.sleep(0.06)


def create_demo_ui(
    root_window: ttk.Window | ttk.Toplevel, io_loop: asyncio.AbstractEventLoop
) -> tuple[ttk.Frame, ttk.Label, ttk.Progressbar]:
    """Create a demo UI and return its dynamic elements."""
    root = ttk.Frame(root_window, padding=10)
    root.pack()

    label = ttk.Label(root, text="")
    label.grid(
        row=0,
        columnspan=3,
        padx=(8, 8),
        pady=(8, 0),
    )

    progressbar = ttk.Progressbar(
        root,
        length=280,
        style=(bootstyle.STRIPED, bootstyle.SUCCESS),  # ty: ignore[invalid-argument-type] -- the type hint for ttk uses strings not tuples
    )
    progressbar.grid(
        row=1,
        columnspan=3,
        padx=(8, 8),
        pady=(16, 0),
    )

    button_block = ttk.Button(
        root,
        text="Sync",
        width=10,
        style=bootstyle.PRIMARY,
        command=functools.partial(calculate_sync, progressbar),
    )
    button_block.grid(
        row=2,
        column=0,
        sticky=tk.W,
        padx=8,
        pady=8,
    )

    theme_combobox = create_theme_combobox(root)
    theme_combobox.grid(
        row=2,
        column=1,
    )

    button_non_block = ttk.Button(
        root,
        text="Async",
        width=10,
        style=bootstyle.INFO,
        command=lambda: io_loop.create_task(calculate_async(progressbar)),
    )
    button_non_block.grid(
        row=2,
        column=2,
        sticky=tk.E,
        padx=8,
        pady=8,
    )
    return root, label, progressbar


def calculate_sync(progressbar: ttk.Progressbar) -> None:
    """Run without yielding to other waiting tasks."""
    limit = 1200000
    for i in range(1, limit):
        progressbar["value"] = i / limit * 100
    progressbar.after(850, functools.partial(progressbar.configure, value=0))


async def calculate_async(progressbar: ttk.Progressbar) -> None:
    """Run but regularly yield execution to other waiting tasks."""
    limit = 1200000
    for i in range(1, limit):
        progressbar["value"] = i / limit * 100
        if i % 1000 == 0:
            await asyncio.sleep(0)
    progressbar.after(850, functools.partial(progressbar.configure, value=0))


def create_theme_combobox(parent: tk.BaseWidget) -> ttk.Combobox:
    """Create and return a Combobox that lists the available themes and handles the selection event."""
    style = ttk.Style.get_instance()
    if not (style and style.theme):
        raise ValueError()
    active_theme = style.theme
    light_themes = []
    dark_themes = []
    for theme_name, definition in ttk_themes.STANDARD_THEMES.items():
        theme_kind = definition["type"]
        if theme_kind == "light":
            light_themes.append(theme_name.capitalize())
        elif theme_kind == "dark":
            dark_themes.append(theme_name.capitalize())
        else:
            raise ValueError()
    sorted_by_kind = [*sorted(light_themes), *sorted(dark_themes)]

    def handle_change_theme(new_selection: str) -> None:
        """Handle the selection event for the theme Combobox."""
        ThemeChanger.use_bootstrap_theme(new_selection.lower(), parent)

    def on_theme_changed(themed_widget: tk.Misc, event_args: tk.Event) -> None:
        """Handle the ThemeChanger.Event.BootstrapThemeChanged event."""
        sending_combobox = themed_widget
        if not isinstance(sending_combobox, ttk.Combobox):
            raise TypeError()
        style = ttk.Style.get_instance()
        if not (style and style.theme):
            raise ValueError()
        sending_combobox.set(style.theme.name.capitalize())

    theme_combobox = create_dropdown_combobox(
        parent,
        values=sorted_by_kind,
        width=12,
        justify=bootstyle.LEFT,
        completion=handle_change_theme,
    )
    theme_combobox.set(active_theme.name.capitalize())
    ThemeChanger.add_handler(theme_combobox, functools.partial(on_theme_changed, theme_combobox))
    return theme_combobox


def show_button_feedback(
    button: ttk.Button,
    command_result: bool,
    success_text: str = "",
    failure_text: str = "",
) -> None:
    """Attach feedback to a ttk.Button command that indicates the command's outcome."""
    normal_text: str = button.cget("text")
    full_style: str = button.cget("style")
    normal_style = tuple(trait.lower() for trait in full_style.split(".")[:-1])

    feedback_text = success_text if command_result else failure_text
    feedback_style = bootstyle.SUCCESS if command_result else bootstyle.DANGER
    button.configure(text=feedback_text, bootstyle=feedback_style)
    button.after(
        850,
        functools.partial(
            button.configure,
            text=normal_text,
            bootstyle=normal_style,
        ),
    )


def create_dropdown_combobox(
    parent: tk.Misc,
    values: list[str],
    width: int,
    justify: bootstyle.Side,
    completion: Callable[[str], None],
) -> ttk.Combobox:
    """Create a ttk.Combobox that only allows selection of entries."""

    def handle_selection(event_args: tk.Event) -> None:
        """Handle the selection event for the combobox."""
        sender = event_args.widget
        if not isinstance(sender, ttk.Combobox):
            raise TypeError()
        sender.selection_clear()
        selected_value = sender.get()
        completion(selected_value)

    combobox = ttk.Combobox(parent, justify=justify, state=bootstyle.READONLY, values=values, width=width)
    combobox.bind("<<ComboboxSelected>>", handle_selection)
    combobox.selection_clear()
    return combobox


def is_left_double_click(mouse_args: mpl_backend_bases.MouseEvent) -> bool:
    """Return True when the mouse_args represent a double-left-click."""
    if mouse_args.button != mpl_backend_bases.MouseButton.LEFT:
        return False
    return mouse_args.dblclick


def get_first_in_range(upper_bound: float, selection: dict) -> Any:  # noqa ANN401: allow callers to select from any collection
    """Get the first value in the selection that is lower than the upper_bound."""
    descending = sorted(selection.keys(), reverse=True)
    first_in_range_index = [upper_bound > entry for entry in descending].index(True)
    first_value_in_range = selection[descending[first_in_range_index]]
    return first_value_in_range


def image_from_icon(name: str, fill: str | None = None, scale_to_width: int | None = None, scale_to_height: int | None = None, scale: float = 1) -> tk.PhotoImage:
    """Look up a FontAwesome icon by name and return it as an PhotoImage object."""
    return icon_to_image(name, fill, scale_to_width, scale_to_height, scale)


def hex_string_for_style(style_name: str, theme_name: str = "") -> str:
    """Return the '#RRGGBB' string for the specified style name for the active or specified theme."""
    if not theme_name:
        style = ttk.Style.get_instance()
        if not (style and style.theme):
            raise ValueError()
        theme_name = style.theme.name
    palette = ttk_themes.STANDARD_THEMES[theme_name]["colors"]
    return palette[style_name]  # ty: ignore[invalid-argument-type] -- the "colors" entry is a dict[str, str]


def open_folder(path: pathlib.Path) -> None:
    """Open Windows Explorer to the specified folder."""
    target = path if path.is_dir() else path.parent
    subprocess.run(["powershell", "-Command", f"Invoke-Item '{target!s}'"], check=True)  # noqa: S603 S607 -- user input not accepted for this call


def toggle_visual_debug(frame: tk.Widget) -> None:
    """Show or hide the border around the specified frame for visual debugging."""
    live_borderwidth = frame.cget("borderwidth")
    new_borderwidth = 1 if live_borderwidth == 0 else 0
    frame.configure(
        {
            "borderwidth": new_borderwidth,
            "relief": tk.FLAT,
        }
    )


def inspect_visual_style(frame: tk.Widget) -> dict:
    """Get visual configuration details for the specified frame and its children."""
    # >>> list(toolbar.children.keys())
    # <<< ['!button', '!button2', '!button3', '!frame', '!checkbutton-1', '!checkbutton-2', '!button4', '!frame2', '!button5', '!label', '!label2']
    #                      button       frame     checkbutton    label
    #  activebackground      x                       x             x
    #  activeforeground      x                       x             x
    #  background            x            x          x             x
    #  disabledforeground    x                       x             x
    #  foreground            x                       x             x
    #  highlightbackground   x            x          x             x
    #  highlightcolor        x            x          x             x
    #  highlightthickness    x            x          x             x
    #  selectcolor                                   x
    theme_properties = [
        "activebackground",
        "activeforeground",
        "background",
        "disabledforeground",
        "foreground",
        "highlightbackground",
        "highlightcolor",
        "highlightthickness",
        "selectcolor",
        "text",
        "command",
    ]
    frame_configuration = {child_name: widget.configure() for child_name, widget in frame.children.items()}
    visual_configuration = {}
    for widget_name, widget_configuration in frame_configuration.items():
        for option_name, option_configuration in widget_configuration.items():
            if option_name not in theme_properties:
                continue
            widget_visual_configuration = visual_configuration.get(widget_name, {})
            widget_visual_configuration[option_name] = option_configuration
            visual_configuration[widget_name] = widget_visual_configuration
    return visual_configuration


def show_palette(palette: dict) -> None:
    """Show the hex color codes for the specified palette."""
    color_names = sorted(ttk_style.Colors.label_iter())
    _ = [logger.info(f"{color:>12} {palette.get(color)}") for color in color_names]


if __name__ == "__main__":
    asyncio.run(AsyncApp.create_and_run(DemoWithAnimation))
