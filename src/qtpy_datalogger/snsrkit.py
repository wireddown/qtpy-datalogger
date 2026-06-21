"""Convenience classes and functions for communicating with QT Py sensor_nodes."""

import json
from typing import Protocol

from qtpy_datalogger import discovery, network, uart
from qtpy_datalogger.sensor_node.snsr.node import classes as node_classes


class IOProtocol(Protocol):
    """A protocol for communicating with QT Py sensor_nodes."""

    async def setup_io(self) -> None:
        """Open a communication channel."""
        ...

    async def send_message(
        self, sensor_node_id: str, command_name: str, command_parameters: dict
    ) -> node_classes.ActionInformation:
        """Send the command and parameters to the specified sensor_node_id."""
        ...

    async def get_response(
        self, sensor_node_id: str, sent_action: node_classes.ActionInformation
    ) -> tuple[dict, node_classes.SenderInformation]:
        """Wait for the sensor_node_id to respond to the specified action and return the result and the node's SenderInformation."""
        ...

    async def close_io(self) -> None:
        """Close the communication channel."""
        ...


def uart_protocol_for_node(sensor_node: discovery.QTPyDevice) -> IOProtocol:
    """Return a new SingleUartProtocol to communicate with the specified sensor_node."""
    return SingleUartProtocol(sensor_node.com_port)


def mqtt_group_protocol_for_node(sensor_node: discovery.QTPyDevice) -> IOProtocol:
    """Return a new MqttGroupProtocol to communicate with the specified sensor_node."""
    return MqttGroupProtocol(sensor_node.mqtt_group_id)


class SingleUartProtocol(IOProtocol):
    """A class that communicates with a single QT Py sensor_node over UART."""

    def __init__(self, uart_port_name: str) -> None:
        """Create a new SingleUartProtocol for the specified uart_port_name."""
        self.port_name = uart_port_name
        self.serial_io = None

    async def setup_io(self) -> None:
        """Open the UART port on the sensor_node."""
        self.serial_io = uart.open_uart(self.port_name)

    async def send_message(
        self, sensor_node_id: str, command_name: str, command_parameters: dict
    ) -> node_classes.ActionInformation:
        """Send the specified command and parameters to the sensor_node over UART."""
        if not self.serial_io:
            message = "UART port is not open. Did you call setup_io()?"
            raise ConnectionError(message)
        payload = node_classes.ActionPayload(
            action=node_classes.ActionInformation(
                command=command_name,
                parameters=command_parameters,
                message_id=f"uart-message-{self.port_name}",
            ),
            sender=node_classes.SenderInformation.create_empty(),
        )
        uart_message = json.dumps(payload.as_dict())
        uart.send_message_as_line(uart_message, self.serial_io)
        return payload.action

    async def get_response(
        self, sensor_node_id: str, sent_action: node_classes.ActionInformation
    ) -> tuple[dict, node_classes.SenderInformation]:
        """Read bytes from the UART on the sensor_node until it completes its response."""
        if not self.serial_io:
            message = "UART port is not open. Did you call setup_io()?"
            raise ConnectionError(message)
        line = await uart.wait_until_line_received(self.serial_io)
        payload = node_classes.ActionPayload.from_dict(json.loads(line))
        return payload.action.parameters, payload.sender

    async def close_io(self) -> None:
        """Close the UART port on the sensor_node."""
        if self.serial_io:
            self.serial_io.close()
            self.serial_io = None


class MqttGroupProtocol(IOProtocol):
    """A class that communicates with a group of QT Py sensor_nodes over MQTT."""

    def __init__(self, mqtt_group: str) -> None:
        """Create a new MqttGroupProtocol for the specified mqtt_group."""
        self.mqtt_group = mqtt_group
        self.qtpy_controller = None

    async def setup_io(self) -> None:
        """Connect a new QTPyController for the sensor_node's group to the MQTT broker."""
        if not self.qtpy_controller:
            self.qtpy_controller = network.QTPyController.for_localhost_server(self.mqtt_group)
            await self.qtpy_controller.connect_and_subscribe()

    async def send_message(
        self, sensor_node_id: str, command_name: str, command_parameters: dict
    ) -> node_classes.ActionInformation:
        """Send the specified command and parameters to the sensor_node over MQTT."""
        if not self.qtpy_controller:
            message = "MQTT connection is not open. Did you call setup_io()?"
            raise ConnectionError(message)
        sent_action = self.qtpy_controller.send_action(sensor_node_id, command_name, command_parameters)
        return sent_action

    async def get_response(
        self, sensor_node_id: str, sent_action: node_classes.ActionInformation
    ) -> tuple[dict, node_classes.SenderInformation]:
        """Monitor MQTT messages until the sensor_node completes its response."""
        if not self.qtpy_controller:
            message = "MQTT connection is not open. Did you call setup_io()?"
            raise ConnectionError(message)
        response_parameters, sender_information = await self.qtpy_controller.get_matching_result(
            sensor_node_id, sent_action
        )
        return response_parameters, sender_information

    async def close_io(self) -> None:
        """Disconnect the QTPyController from the MQTT broker."""
        if self.qtpy_controller:
            await self.qtpy_controller.disconnect()
            self.qtpy_controller = None
