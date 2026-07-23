"""Host-side app that plots analog data using the stock QT Py sensor node runtime."""

import asyncio
import json
import logging
import time
import tkinter as tk
from tkinter import font

import matplotlib.backend_bases as mpl_backend_bases
import numpy as np
import serial
import ttkbootstrap as ttk
from matplotlib.figure import Figure

from qtpy_datalogger import datatypes, discovery, guikit, network, ttkbootstrap_matplotlib, uart
from qtpy_datalogger.sensor_node.snsr.node import classes as node_classes
from qtpy_datalogger.sensor_node.snsr.node import mqtt as node_mqtt

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)


class AnalogPlotter(guikit.AsyncWindow):
    """Host-side app that plots analog data using the stock QT Py sensor node runtime."""

    def create_user_interface(self) -> None:
        """Create the main window and connect event handlers."""
        self.root_window.title("Analog Plotter • qtpy-datalogger demo app")
        self.root_window.minsize(width=870, height=600)
        self.root_window.columnconfigure(0, weight=1)
        self.root_window.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root_window, name="main_frame", padding=16)
        main.grid(column=0, row=0, sticky=tk.NSEW)
        main.columnconfigure(0, weight=1)  # One column with visuals vertically stacked in rows
        main.rowconfigure(0, weight=0)  # - Title
        main.rowconfigure(1, weight=1)  # - matplotlib canvas
        main.rowconfigure(2, weight=0)  # - matplotlib toolbar

        title_font = font.Font(weight="bold", size=16)
        title_label = ttk.Label(main, text="Analog Plotter", font=title_font)
        title_label.grid(column=0, row=0)

        canvas_frame = ttk.Frame(main, name="canvas_frame")
        canvas_frame.grid(column=0, row=1, sticky=tk.NSEW)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        figure_aspect = (4, 3)
        figure_dpi = 100
        mpl_figure = Figure(figsize=figure_aspect, dpi=figure_dpi)
        self.axes = mpl_figure.add_subplot()
        self.axes.set_xlim(0, 120)
        self.axes.set_ylim(0, 3.5)
        self.time_axis_label = self.axes.set_xlabel("Time (s)", picker=True)  # Enable picking to generate mouse events
        self.y_axis_label = self.axes.set_ylabel("Volts", picker=True)  # Enable picking to generate mouse events
        self.axes.grid(
            visible=True,
            which="major",
            axis="y",
            dashes=(3, 8),
            zorder=-1,
        )

        self.axis_tool_window = None
        self.background_tasks = set()
        self.canvas = ttkbootstrap_matplotlib.create_styled_plot_canvas(mpl_figure, canvas_frame)
        self.canvas.mpl_connect("key_press_event", mpl_backend_bases.key_press_handler)
        self.canvas.mpl_connect("button_press_event", self.on_graph_mouse_down)
        self.canvas.mpl_connect("pick_event", self.on_graph_pick)

        toolbar_row = ttk.Frame(main, name="toolbar_row")
        toolbar_row.grid(column=0, row=2, padx=(40, 80), sticky=tk.EW)
        toolbar_row.columnconfigure(0, weight=1)  # Left side spacer
        toolbar_row.columnconfigure(1, weight=0)  # matplotlib toolbar

        left_side_spacer = ttk.Frame(toolbar_row, name="side_spacer")
        left_side_spacer.grid(column=0, row=0, sticky=tk.NSEW)

        toolbar_frame = ttkbootstrap_matplotlib.create_styled_plot_toolbar(toolbar_row, self.canvas)
        toolbar_frame.grid(column=1, row=0, sticky=tk.EW)

        theme_name = "darkly"
        style = ttk.Style.get_instance()
        if not style:
            raise ValueError()
        guikit.ThemeChanger.use_bootstrap_theme(theme_name, self.root_window)

        # Bookkeeping
        self.time_0 = time.monotonic()
        self.mqtt_controller = None
        self.mqtt_task = None
        self.uart = None
        self.uart_task = None

    async def on_showing(self) -> None:
        """Initialize window before entering main loop."""

    async def on_loop(self) -> None:
        """Update the window with new information."""
        await self.get_and_plot_data()

    async def on_closing(self) -> None:
        """Finalize the window after exiting main loop."""
        await self.close_io()

    def on_graph_mouse_down(self, event_args: mpl_backend_bases.Event) -> None:
        """Handle mouse-down events from the graph."""
        if type(event_args) is not mpl_backend_bases.MouseEvent:
            return
        if not guikit.is_left_double_click(event_args):
            return
        clicked = event_args.inaxes
        if clicked is not self.axes:
            return

        limits = guikit.Range.create_infinite()
        axis_tool_window = self.ensure_tool_window()
        axis_tool_window.attach_to_axis(event_args.canvas.draw_idle, self.axes, guikit.AxisToolDialog.Axis.Y, limits)

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

        limits = guikit.Range.create_infinite()
        axis_tool_window = self.ensure_tool_window()
        axis_tool_window.attach_to_axis(event_args.canvas.draw_idle, self.axes, axis, limits)

    def ensure_tool_window(self) -> guikit.AxisToolDialog:
        """Open an AxisToolDialog on the specified axis."""
        if not self.axis_tool_window:
            self.axis_tool_window = guikit.AxisToolDialog(self.root_window)
            open_tool_window_task = asyncio.create_task(self.axis_tool_window.show(guikit.DialogBehavior.Modeless))
            self.background_tasks.add(open_tool_window_task)
            open_tool_window_task.add_done_callback(self.finalize_tool_window)
        return self.axis_tool_window

    def finalize_tool_window(self, task: asyncio.Task[object]) -> None:
        """Finalize the AxisToolDialog after the user closes it."""
        self.axis_tool_window = None
        self.background_tasks.discard(task)

    async def get_and_plot_data(self) -> None:
        """Discover nodes and request an analog voltage measurement."""
        # # # # # # # # # # # # # # # # # # # # # # # # # #
        #
        #  Demo: Simple unoptimized approach without error handling or cancellation
        #

        # Customize
        use_uart = True
        use_mqtt = False
        minimum_mqtt_node_count = 1
        channel_cmd_string = "A0 A3"
        mqtt_group = datatypes.Default.MqttGroup
        max_adc_voltage = 3.3
        max_adc_code = 2**16

        # Loop variables
        new_data = {}
        time_coordinate = time.monotonic() - self.time_0
        channels = channel_cmd_string.split(" ")
        analog_action = node_classes.ActionInformation(
            command="custom",
            parameters={"input": f"qtpycmd read {channel_cmd_string}"},
            message_id="analog-plotter-1",
        )

        def process_read_response(response: str) -> list[float]:
            """Parse the response and scale the ADC data."""
            closing_index = response.index("]")
            json_substring = response[: closing_index + 1]
            adc_codes = json.loads(json_substring)
            voltages = [adc_code * (max_adc_voltage / max_adc_code) for adc_code in adc_codes]
            return voltages

        # # # # # # # # # # # # # # # # # # # # # # # # # #
        #
        #  UART state machine
        #
        if use_uart and not self.uart:
            # Do UART-only scan with empty group_id
            uart_nodes = await discovery.discover_qtpy_devices_async(group_id="")
            if uart_nodes:
                first_node_key = sorted(uart_nodes)[0]
                first_node = uart_nodes[first_node_key]
                self.uart = uart.open_uart(first_node.com_port)

        if self.uart and not self.uart_task:

            async def do_serial_read(com_port: serial.Serial) -> tuple[str, list[float]]:
                read_command = analog_action.parameters["input"]
                uart.send_message_as_line(read_command, com_port)
                response = await uart.wait_until_line_received(com_port)
                voltages = process_read_response(response)
                return (str(com_port.name), voltages)

            self.uart_task = asyncio.create_task(do_serial_read(self.uart))

        # Many loops later...
        if self.uart_task and self.uart_task.done():
            node_name, voltages = self.uart_task.result()
            logger.info(f"{time_coordinate:.5f}  ==UART==  received  {node_name}")
            new_data[node_name] = voltages
            self.uart_task = None

        # # # # # # # # # # # # # # # # # # # # # # # # # #
        #
        #  MQTT state machine
        #
        if use_mqtt and not self.mqtt_controller:
            self.mqtt_controller = network.QTPyController.for_localhost_server(group_id=mqtt_group)
            await self.mqtt_controller.connect_and_subscribe()

        if self.mqtt_controller and not self.mqtt_task:

            async def do_mqtt_collect(mqtt_controller: network.QTPyController) -> dict[str, list[float]]:
                mqtt_node_readings = {}
                logger.info(f"Waiting for {minimum_mqtt_node_count} nodes to respond via MQTT")
                mqtt_controller.post_retained_group_action(analog_action)
                while len(mqtt_node_readings) < minimum_mqtt_node_count:
                    result, sender = await mqtt_controller.wait_until_matching_node_response(action=analog_action)
                    voltages = process_read_response(result["output"])
                    mqtt_node = node_mqtt.node_from_topic(sender.descriptor_topic).split("-")[1]
                    mqtt_node_readings[mqtt_node] = voltages
                return mqtt_node_readings

            self.mqtt_task = asyncio.create_task(do_mqtt_collect(self.mqtt_controller))

        # Many loops later...
        if self.mqtt_controller and self.mqtt_task and self.mqtt_task.done():
            mqtt_node_voltages = self.mqtt_task.result()
            for node_name, voltages in mqtt_node_voltages.items():
                logger.info(f"{time_coordinate:.5f}  ::MQTT::  received  {node_name}")
                new_data[node_name] = voltages
            self.mqtt_controller.clear_retained_group_action()
            self.mqtt_task = None

        # # # # # # # # # # # # # # # # # # # # # # # # # #
        #
        #  Without any new data, briefly yield and return
        #
        if not new_data:
            await asyncio.sleep(1e-3)
            return

        # # # # # # # # # # # # # # # # # # # # # # # # # #
        #
        #  Create and update plots
        #
        time_stamp = [time_coordinate]
        if not self.axes.lines:
            self.axes.set_title(f"Sensor node voltage for pins {', '.join(channels)}")
            for node, data in new_data.items():
                for channel_name, channel_data in zip(channels, data, strict=True):
                    self.axes.plot(time_stamp, channel_data, label=f"{node}-{channel_name}")
        else:
            active_plots = {str(line.get_label()): line for line in self.axes.lines}
            plotted_nodes_with_channels = set(active_plots.keys())
            new_data_nodes = set(new_data.keys())
            plotted_nodes_alone = set(name.split("-")[0] for name in plotted_nodes_with_channels)
            new_nodes_with_channels = set(
                f"{node_name}-{channel_name}" for node_name in new_data_nodes for channel_name in channels
            )
            updated_plot_names = sorted(new_nodes_with_channels.intersection(plotted_nodes_with_channels))

            unplotted_nodes = sorted(new_data_nodes - plotted_nodes_alone)
            for node in unplotted_nodes:
                for channel_name, channel_data in zip(channels, new_data[node], strict=True):
                    self.axes.plot(time_stamp, channel_data, label=f"{node}-{channel_name}")

            updated_plots = {name: active_plots[name] for name in updated_plot_names}
            for line_name, plot_line in updated_plots.items():
                node_name, channel_name = line_name.split("-")
                channel_index = channels.index(channel_name)
                new_y_data = new_data[node_name][channel_index]
                line_x = plot_line.get_xdata()
                new_x = np.append(line_x, time_stamp)
                line_y = plot_line.get_ydata()
                new_y = np.append(line_y, new_y_data)
                plot_line.set_xdata(new_x)
                plot_line.set_ydata(new_y)
        self.axes.legend()
        self.canvas.draw()

    async def close_io(self) -> None:
        """Close all communication channels and release system resources."""
        if self.uart:
            if self.uart_task:
                logger.info("Clearing active UART message")
                _ = await self.uart_task
                self.uart_task = None
            logger.info("Closing UART connection")
            self.uart.close()
            self.uart = None

        if self.mqtt_controller:
            if self.mqtt_task:
                logger.info("Clearing retained MQTT message")
                self.mqtt_controller.clear_retained_group_action()
                try:
                    async with asyncio.timeout(5.0):
                        _ = await self.mqtt_task
                except TimeoutError:
                    pass
                finally:
                    self.mqtt_task = None
            logger.info("Closing MQTT connection")
            _ = self.mqtt_controller.clear_messages()
            await self.mqtt_controller.disconnect()
            self.mqtt_controller = None


if __name__ == "__main__":
    asyncio.run(guikit.AsyncApp.create_and_run(AnalogPlotter))
