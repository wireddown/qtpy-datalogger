"""Functions and classes for communicating with QT Py sensor nodes over serial ports."""

import asyncio
import contextlib
import logging

import serial
from serial.tools import miniterm as mt

from qtpy_datalogger.datatypes import DetailKey

logger = logging.getLogger(__name__)


def query_ports_from_serial() -> dict[str, dict[DetailKey, str]]:
    """
    Scan the system for serial ports and return a dictionary of information.

    Returned entries, grouped by com_port
    - com_port
    - com_id
    - serial_number
    """
    # Other approaches include WMI's Win32_SerialPort
    from serial.tools.list_ports_windows import comports  # noqa: PLC0415 -- dynamic import at runtime for Windows

    discovered_comports = {
        comport.device: {
            DetailKey.com_port: comport.device,
            DetailKey.com_id: comport.hwid,
            DetailKey.serial_number: comport.serial_number,
        }
        for comport in sorted(comports())
        if comport.device != "COM1"
    }
    logger.debug(discovered_comports)
    return discovered_comports


def open_session_on_port(port: str) -> None:
    """Open a terminal connection to the specified serial port."""
    serial_options = _get_default_uart_options(port)
    logger.debug(serial_options)
    com_port = serial.serial_for_url(**serial_options)

    if not hasattr(com_port, "cancel_read"):
        # Enable timeout for alive flag polling if cancel_read is not available
        com_port.timeout = 1

    if isinstance(com_port, serial.Serial):
        com_port.exclusive = True

    com_port.open()

    miniterm_options = {
        "serial_instance": com_port,
        "echo": False,
        "eol": "crlf",
        "filters": ["direct"],
    }
    logger.debug(miniterm_options)
    miniterm = mt.Miniterm(**miniterm_options)

    miniterm.exit_character = "\x1d"
    miniterm.menu_character = "\x14"
    miniterm.raw = False
    miniterm.set_rx_encoding("UTF-8")
    miniterm.set_tx_encoding("UTF-8")

    quit_command = mt.key_description(miniterm.exit_character)
    help_command = mt.key_description(miniterm.menu_character)
    logger.info(
        f"---   Miniterm on {miniterm.serial.name}   Opts: {miniterm.serial.baudrate},{miniterm.serial.bytesize},{miniterm.serial.parity},{miniterm.serial.stopbits}    ---"
    )
    logger.info(f"---   Quit: {quit_command}        Help: {help_command} then H   ---")

    miniterm.start()
    with contextlib.suppress(KeyboardInterrupt):
        miniterm.join(True)
    miniterm.join()
    miniterm.close()

    logger.info("")
    logger.info(f"Reconnect with 'qtpy-datalogger connect --port {port}'")


def open_uart(port: str) -> serial.Serial:
    """Open a UART connection to the specified serial port and return the opened UART."""
    if port == "COM1":
        logger.error(f"Opening '{port}' is not supported.")
        raise ValueError

    serial_options = _get_default_uart_options(port)
    serial_options.update(
        {
            "timeout": 0,
            "write_timeout": 0,
        }
    )
    logger.debug(serial_options)
    com_port = serial.serial_for_url(**serial_options)

    if isinstance(com_port, serial.Serial):
        com_port.exclusive = True

    com_port.open()
    com_port.reset_input_buffer()
    com_port.reset_output_buffer()
    return com_port


def send_message_as_line(message: str, com_port: serial.Serial) -> None:
    """Append a newline to the message, encode it, and write it to the UART."""
    with_newline = f"{message.strip()}\n"
    uart_bytes = with_newline.encode()
    logger.debug(uart_bytes)
    com_port.write(uart_bytes)
    com_port.flush()


async def wait_until_line_received(com_port: serial.Serial) -> str:
    """Cooperatively read bytes from the UART until receiving a newline. Decode the bytes and return the response."""
    input_buffer = bytearray()
    end_of_response = b"\r\n"
    while not input_buffer.endswith(end_of_response):
        if not com_port.in_waiting:
            await asyncio.sleep(1e-3)
            continue
        new_bytes = com_port.read(1024)
        if new_bytes:
            logger.debug(new_bytes)
            input_buffer.extend(new_bytes)
    response = input_buffer.decode().splitlines()[-1]
    return response


def _get_default_uart_options(port: str) -> dict[str, str | int | bool]:
    """Get the default serial port options for QT Py devices."""
    return {
        "url": port,
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "rtscts": False,
        "xonxoff": False,
        "do_not_open": True,
    }
