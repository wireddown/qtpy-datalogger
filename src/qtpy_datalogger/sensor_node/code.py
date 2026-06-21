"""code.py file is the main loop from qtpy_datalogger.sensor_node."""

from gc import collect
from json import dumps
from time import monotonic, sleep
from traceback import print_exception

from adafruit_minimqtt.adafruit_minimqtt import MMQTTException
from snsr.core import get_app, read_one_uart_line
from snsr.handlers import can_handle_message, get_sender_information
from snsr.node.classes import ActionPayload
from snsr.node.mqtt import get_broadcast_topic, get_command_topic, get_descriptor_topic
from snsr.rxtx import connect_and_subscribe, create_mqtt_client, unsubscribe_and_disconnect
from snsr.settings import settings

settings.boot_time = monotonic()
mqtt_topics = [
    get_broadcast_topic(settings.node_group),
    get_command_topic(settings.node_group, settings.mqtt_client_id),
]


def main_loop(skip_mqtt: bool) -> str:
    """Run the main node loop."""
    mqtt_client = None
    if not skip_mqtt:
        settings.connect_to_wifi()
        mqtt_client = create_mqtt_client(settings.node_group, settings.mqtt_client_id)
        connect_and_subscribe(mqtt_client, mqtt_topics)

    uart_input = ""
    while uart_input.lower() not in ["exit", "quit"]:
        uart_connected = settings.uart_connected
        if mqtt_client:
            did_receive = mqtt_client.loop(timeout=1.0)  # Smallest supported timeout
            if not (did_receive or uart_connected):
                sleep(4)  # Conserve battery by not constantly polling the network

        if uart_connected:
            sleep(0.2)
            if not settings.uart_bytes_waiting:
                continue
            uart_input = read_one_uart_line(message="")
            action_payload = can_handle_message(uart_input)
            made_custom = False
            if not action_payload:
                action_payload = ActionPayload.create_custom_with_input(uart_input.strip())
                made_custom = True

            app = get_app(action_payload.action)
            result = app.handle_message()

            if made_custom:
                response = result.parameters["output"]
            else:
                descriptor_topic = get_descriptor_topic(settings.node_group, settings.mqtt_client_id)
                sender_information = get_sender_information(descriptor_topic)
                result_payload = ActionPayload(result, sender_information)
                response = dumps(result_payload.as_dict())
            print(response)

            app.did_handle_message()

    if mqtt_client:
        unsubscribe_and_disconnect(mqtt_client, mqtt_topics)
    return uart_input


most_recent_error = type(None)
error_count = 0
error_limit = 3
while True:
    try:
        wifi_failed = most_recent_error is ConnectionError
        mqtt_failed = most_recent_error is MMQTTException
        skip_mqtt = settings.uart_connected and (wifi_failed or mqtt_failed)
        if skip_mqtt:
            reason = "incorrect WiFi credentials" if wifi_failed else "broker is unreachable"
            print(f"[SNSR]  Disabling MQTT: {reason}")
        result = main_loop(skip_mqtt)
        if result.lower() in ["exit", "quit"]:
            print("[SNSR]  Exiting to REPL...")
            break
    except Exception as e:
        try:
            settings.disconnect_from_wifi()
        except AttributeError:
            pass
        print()
        print(f"[SNSR]  Encountered {type(e).__name__}")
        print_exception(e)
        collect()
        if type(e) is most_recent_error:
            error_count = error_count + 1
            if error_count >= error_limit:
                raise
        else:
            most_recent_error = type(e)
            error_count = 0
        print("[SNSR]  Trying again...")
        continue
