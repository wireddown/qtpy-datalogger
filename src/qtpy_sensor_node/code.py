"""Main program for QT Py DAQ sensor Node."""

import time

import adafruit_adxl37x
import analogio
import board
import microcontroller
import neopixel
import supervisor
import struct
import time
import wifi


DEVICE_ID = wifi.radio.mac_address.hex()


### Accelerometer ADXL375

# The board API for I2C bus clock is always 100kHz
# - https://github.com/adafruit/circuitpython/blob/68cdc535b2f299bdfbb90d88e04b09cd5d2b40d4/shared-module/board/__init__.c#L71C88-L71C94
# To change frequency, create the I2C bus explicitly using 'I2C()' from busio
# - https://docs.circuitpython.org/en/stable/shared-bindings/busio/index.html#busio.I2C

# Spec pg 18
# "For example, using I2C mode at 100 kHz limits the maximum ODR to 200 Hz. Operation at an
# output data rate above the recommended maximum value may result in undesirable effects
# on the acceleration data, including missing samples or additional noise."

# Default data rate is 100 Hz
# - The Python module leaves it unchanged from the device's power-on value
# However, it is possible to increase the output data rate to 200 Hz and do self-test.

# 0 g output for XOUT, YOUT, ZOUT: ±400 mg
# X/Y/Z sensitivity: 18.4..22.6 (20.5 LSB/g typ)
# Scale factor: 0.044..0.054 g/LSB (49 mg/LSB typ)
XL3D_SCALE_G_PER_LSB = 49e-3  # 44e-3 # 49e-3 # 54e-3  # How to measure?
XL3D_OFFSET_G_PER_LSB = 196e-3  # From spec

XL3D_Z_SENSITIVITY_LSB_PER_G = 1 / XL3D_SCALE_G_PER_LSB
XL3D_LSB_PER_OFFSET_REGISTER_LSB = XL3D_OFFSET_G_PER_LSB / XL3D_SCALE_G_PER_LSB

# One-time offset calibration

# 44:  HW Adj: [0.300816, 0.507347, -2.02653] units: 0.196 g per LSB
# 54:  HW Adj: [0.319592, 0.600612, -1.25316] units: 0.196 g per LSB

# 46: SW Trim: [1.35, 2.27, -3.97914] units: 0.046 g per LSB
# 49: SW Trim: [1.32, 2.15, -2.54816] units: 0.049 g per LSB
# 54: SW Trim: [1.29, 2.16, -0.758528] units: 0.054 g per LSB

# I want to try a flip-test and compare +Z with -Z to learn whether this helps find sensitivity and offset

# Spec pg 21
# The OFSX, OFSY, and OFSZ registers contain user-configured offset adjustments in twos
# complement format with a scale factor of 0.196 g/LSB. The value stored in the offset registers
# is automatically added to the acceleration data, and the resulting value is stored in the
# output data registers (Address 0x32 to Address 0x37).

# Unit 1
# XL3D_HARDWARE_OFFSET = [-1, 1, 1]
# XL3D_SOFTWARE_TRIM_OFFSET = [-2.14, 1.5, 1.08]

# Unit 2
# XL3D_HARDWARE_OFFSET = [-3, -1, 1]
# XL3D_SOFTWARE_TRIM_OFFSET = [-1.1, -2.3, 1.1]

# Unit 3
#XL3D_HARDWARE_OFFSET = [-3, 0, 1]
#XL3D_SOFTWARE_TRIM_OFFSET = [-1.4, -2.1, 2.65]
XL3D_HARDWARE_OFFSET = [-3, 0, 1]
XL3D_SOFTWARE_TRIM_OFFSET = [0, 0, 0]

# new unit
# XL3D_HARDWARE_OFFSET = [0, 0, 0]
# XL3D_SOFTWARE_TRIM_OFFSET = [0, 0, 0]


### NeoPixel


ORDER = neopixel.GRB
num_pixels = 1
pixel_pin = board.NEOPIXEL

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=ORDER
)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colors are a transition R - G - B - back to R.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)


### Self diagnostics


def qtpys3_pin_list():
    board_pins = []
    for pin in dir(microcontroller.pin):
        if (isinstance(getattr(microcontroller.pin, pin), microcontroller.Pin)):
            pins = []
            for alias in dir(board):
                if getattr(board, alias) is getattr(microcontroller.pin, pin):
                    pins.append(f"board.{alias}")
            # Add the original GPIO name in parentheses.
            if pins:
                # Only include pins that are in the board.
                pins.append(f"({str(pin)})")
                board_pins.append(" ".join(pins))

    for pins in sorted(board_pins):
        print(pins)


def sensor_scan(accelerometer, ai_channels):
    pixels.fill((255, 0, 0))
    pixels.show()

    take = 100
    J1_SENSE = ai_channels["AI0"]
    J2_SENSE = ai_channels["AI1"]
    J3_SENSE = ai_channels["AI2"]
    J4_SENSE = ai_channels["AI3"]
    J5_SENSE = ai_channels["AI4"]
    J6_SENSE = ai_channels["AI5"]
    TEMP_SENSE = ai_channels["AI6"]
    BATT_SENSE = ai_channels["AI7"]
    adxl375_raw = xl3d_take_n(accelerometer, count=20)

    print()
    print("    XL range:", accelerometer.range)
    print("   XL offset:", accelerometer.offset)
    print("      raw XL:", adxl375_raw)
    print("     ADXL375:", xl3d_apply_scaling(adxl375_raw), "g")
    print()
    print("    AI range:", TEMP_SENSE.reference_voltage)
    print("    avg TEMP:", adc_take_n(TEMP_SENSE, take))
    print("    avg BATT:", adc_take_n(BATT_SENSE, take))
    for index, junction in enumerate([J1_SENSE, J2_SENSE, J3_SENSE, J4_SENSE, J5_SENSE, J6_SENSE]):
        junction_number = index + 1
        print(f"   avg Jctn{junction_number}:", adc_take_n(junction, take))
    pixels.fill((0, 255, 0))
    pixels.show()
    time.sleep(.5)
    rainbow_cycle(wait=0.002)


def run_sensor_scan_loop():
    accelerometer = ADXL375_Helper(XL3D_HARDWARE_OFFSET).accelerometer
    with Reserve_AI_Channels() as all_analog_channels:
        while not supervisor.runtime.serial_bytes_available:
            # Any key to advance
            print()
            print("Scanning all sensors... Press ENTER to exit.")
            sensor_scan(accelerometer, all_analog_channels)
            time.sleep(0.7)
        _ = input().strip()


### Analog input
# https://docs.circuitpython.org/en/stable/shared-bindings/analogbufio/index.html#analogbufio.BufferedIn


class Reserve_AI_Channels():
    def _reserve_all_channels(self):
        self.all_channels = {
            "AI0": analogio.AnalogIn(board.A0),
            "AI1": analogio.AnalogIn(board.A1),
            "AI2": analogio.AnalogIn(board.A2),
            "AI3": analogio.AnalogIn(board.A3),
            "AI4": analogio.AnalogIn(board.A4),
            "AI5": analogio.AnalogIn(board.A5),
            "AI6": analogio.AnalogIn(board.A6),
            "AI7": analogio.AnalogIn(board.A7),
        }
        return self.all_channels

    def _release_all_channels(self):
        for name, pin in self.all_channels.items():
            pin.deinit()

    def __enter__(self):
        return self._reserve_all_channels()

    def __exit__(self, exc_type, exc_value, traceback):
        self._release_all_channels()


def adc_take_n(from_ai_pin, count):
    total = 0
    for _ in range(count):
        total = total + from_ai_pin.value
    average = total / count
    return average


def adc_format_characterization_header():
    return ",".join(["QTPy channel", "Samples averaged", "ADC code", "QTPy identifier", "timestamp (ns)"])


def adc_format_characterization_row(channel_name, samples_averaged, adc_code, timestamp):
    row = [channel_name, f"{samples_averaged}", f"{adc_code}", DEVICE_ID, f"{timestamp:d}"]
    return ",".join(row)


def analog_input_characterization_scan(channels, samples_to_average):
    for channel_name, analog_input in sorted(channels.items()):
        average_channel_code = adc_take_n(analog_input, samples_to_average)
        row = adc_format_characterization_row(
            channel_name=channel_name,
            samples_averaged=samples_to_average,
            adc_code=average_channel_code,
            timestamp=time.monotonic_ns()
        )
        print(row)


def run_analog_input_characterization_loop():
    with Reserve_AI_Channels() as analog_input_channels:
        data_column_names = adc_format_characterization_header()
        while not supervisor.runtime.serial_bytes_available:
            # Any key to advance
            print()
            print("Monitoring analog input channels... press ENTER to run ADC characterization scan.")

            print()
            print(data_column_names)
            analog_input_characterization_scan(analog_input_channels, samples_to_average=20)

            time.sleep(0.7)
        _ = input().strip()

        repeat_count = 30
        samples_to_average_list = [1, 10, 20, 50, 100, 200, 500, 1000, 2000]
        print()
        print(data_column_names)
        for _ in range(repeat_count):
            for samples_to_average in samples_to_average_list:
                analog_input_characterization_scan(analog_input_channels, samples_to_average)

        print()
        print("Scan complete. Press ENTER to exit.")
        while not supervisor.runtime.serial_bytes_available:
            # Any key to advance
            time.sleep(0.7)
        _ = input().strip()


### Accelerometer ADXL375


class ADXL375_Helper():
    def __init__(
            self,
            hardware_offset = None,
        ):
        i2c = board.STEMMA_I2C()  # Singleton, lock-free atomic facade
        accelerometer = adafruit_adxl37x.ADXL375(i2c)
        accelerometer.range = adafruit_adxl37x.Range.RANGE_200_G
        adxl_hardware_offset = hardware_offset if hardware_offset else [0, 0, 0]
        accelerometer.offset = adxl_hardware_offset
        self.adxl375 = accelerometer

    @property
    def accelerometer(self):
        return self.adxl375


def xl3d_register_scan(accelerometer):
    print("  Addr : Hex  Py")
    for register in [
        adafruit_adxl37x._REG_DEVID,
        adafruit_adxl37x._REG_BW_RATE,
        adafruit_adxl37x._REG_POWER_CTL,
        adafruit_adxl37x._REG_INT_ENABLE,
        adafruit_adxl37x._REG_INT_MAP,
        adafruit_adxl37x._REG_DATA_FORMAT,
        adafruit_adxl37x._REG_FIFO_CTL,
        adafruit_adxl37x._REG_FIFO_STATUS,
    ]:
        byte_count = 1
        as_bytes = accelerometer._read_register(register, byte_count)
        as_py = accelerometer._read_register_unpacked(register)
        print("  0x%02X : 0x%s % 03X" % (register, as_bytes.hex().upper(), as_py))


def xl3d_read_all_axes(from_accelerometer):
    byte_count = 6
    raw_bytes = from_accelerometer._read_register(adafruit_adxl37x._REG_DATAX0, byte_count)
    x, y, z = struct.unpack("<hhh", raw_bytes)
    return [x, y, z]


def xl3d_take_n(from_accelerometer, count):
    xl3d_data_rate = 100
    xl3d_clock_period = 1 / xl3d_data_rate
    spacial_axes = ["raw_x", "raw_y", "raw_z"]
    xl3d_total = {
        spacial_axis: 0
        for spacial_axis in spacial_axes
    }
    for _ in range(count):
        all_raw_3dxl = xl3d_read_all_axes(from_accelerometer)
        for spacial_axis, raw_value in zip(spacial_axes, all_raw_3dxl):
            xl3d_total[spacial_axis] += raw_value
        time.sleep(xl3d_clock_period)
    average = [
        xl3d_total[spacial_axis] / count
        for spacial_axis in spacial_axes
    ]
    return average


def xl3d_format_characterization_header():
    return ",".join(["Samples averaged", "Raw X", "Raw Y", "Raw Z", "QTPy identifier", "timestamp (ns)"])


def xl3d_format_characterization_row(samples_averaged, raw_x, raw_y, raw_z, timestamp):
    row = [f"{samples_averaged}", f"{raw_x}", f"{raw_y}", f"{raw_z}", DEVICE_ID, f"{timestamp:d}"]
    return ",".join(row)


def xl3d_apply_software_offset_trim(all_xl3d_axes_raw):
    trimmed = [
        (dimension + software_trim)
        for dimension, software_trim in zip(all_xl3d_axes_raw, XL3D_SOFTWARE_TRIM_OFFSET)
    ]
    return trimmed


def xl3d_apply_scaling(all_xl3d_axes_raw):
    scaled = [
        dimension * XL3D_SCALE_G_PER_LSB
        for dimension in all_xl3d_axes_raw
    ]
    return scaled


def xl3d_characterization_scan(accelerometer, samples_to_average):
    all_xl3d = xl3d_take_n(accelerometer, samples_to_average)
    trimmed = xl3d_apply_software_offset_trim(all_xl3d)
    row = xl3d_format_characterization_row(
        samples_averaged=samples_to_average,
        raw_x=trimmed[0],
        raw_y=trimmed[1],
        raw_z=trimmed[2],
        timestamp=time.monotonic_ns(),
    )
    print(row)


def run_accelerometer_offset_loop():
    accelerometer = ADXL375_Helper(XL3D_HARDWARE_OFFSET).accelerometer
    while not supervisor.runtime.serial_bytes_available:
        # Any key to advance
        print()
        print("Monitoring XL3D offset... press ENTER to exit.")

        xl3d_raw = xl3d_take_n(accelerometer, count=100)
        trimmed = xl3d_apply_software_offset_trim(xl3d_raw)
        scaled = xl3d_apply_scaling(trimmed)

        as_offset = [
            dimension / XL3D_OFFSET_G_PER_LSB
            for dimension in scaled
        ]

        z_1g_offset = (scaled[-1] - 1) / XL3D_OFFSET_G_PER_LSB
        as_offset[-1] = z_1g_offset

        print()
        print("Accelerometer registers")
        xl3d_register_scan(accelerometer)

        print()
        as_trim = [0 for x in as_offset]
        for index, offset in enumerate(as_offset):
            if abs(offset) < 1:
                print(f"Hardware offset set correctly for axis{index}. Calculating SW trim.")
                as_trim[index] = offset * XL3D_LSB_PER_OFFSET_REGISTER_LSB

        print()
        print("Accelerometer state")
        print("   Range:", accelerometer.range)
        print("  Offset:", accelerometer.offset, f"units: {XL3D_OFFSET_G_PER_LSB} g per LSB")
        print(" SW trim:", XL3D_SOFTWARE_TRIM_OFFSET, f"units: {XL3D_SCALE_G_PER_LSB} g per LSB")
        print("     Raw:", xl3d_raw, f"units: {XL3D_SCALE_G_PER_LSB} g per LSB")
        print(" Trimmed:", trimmed, f"units: {XL3D_SCALE_G_PER_LSB} g per LSB")
        print("  Scaled:", scaled, "units: g")
        print("  HW Adj:", as_offset, f"units: {XL3D_OFFSET_G_PER_LSB} g per LSB")
        print(" SW Trim:", as_trim, f"units: {XL3D_SCALE_G_PER_LSB} g per LSB")

        # No need to wait: reading from the accelerometer takes long enough
    _ = input().strip()


def run_accelerometer_self_test_loop():
    accelerometer = ADXL375_Helper(XL3D_HARDWARE_OFFSET).accelerometer

    while not supervisor.runtime.serial_bytes_available:
        # Any key to advance
        print()
        print("Looping XL3D self test... press ENTER to exit.")

        # Baseline
        xl3d_raw = xl3d_take_n(accelerometer, count=100)
        trimmed = xl3d_apply_software_offset_trim(xl3d_raw)
        scaled = xl3d_apply_scaling(trimmed)

        # Enable self test
        format_register = accelerometer._read_register_unpacked(adafruit_adxl37x._REG_DATA_FORMAT)
        format_register |= 0x80
        accelerometer._write_register_byte(adafruit_adxl37x._REG_DATA_FORMAT, format_register)

        # Throw away 5 samples while the sensor settles
        _ = xl3d_take_n(accelerometer, count=5)

        # Measure
        xl3d_raw_self_test = xl3d_take_n(accelerometer, count=100)
        self_test_trimmed = xl3d_apply_software_offset_trim(xl3d_raw_self_test)
        self_test_scaled = xl3d_apply_scaling(self_test_trimmed)

        # Disable self test
        format_register = accelerometer._read_register_unpacked(adafruit_adxl37x._REG_DATA_FORMAT)
        format_register &= ~0x80
        accelerometer._write_register_byte(adafruit_adxl37x._REG_DATA_FORMAT, format_register)

        # Throw away 5 samples while the sensor settles
        _ = xl3d_take_n(accelerometer, count=5)

        # Compare
        delta_trimmed = [
            self_test - baseline
            for self_test, baseline in zip(self_test_trimmed, trimmed)
        ]
        delta_scaled = [
            self_test - baseline
            for self_test, baseline in zip (self_test_scaled, scaled)
        ]

        # Print results
        print()
        print("Accelerometer self test")
        print("  Baseline trimmed:", trimmed)
        print(" Self test trimmed:", self_test_trimmed)
        print("     Delta trimmed:", delta_trimmed)
        print("   Baseline scaled:", scaled)
        print("  Self test scaled:", self_test_scaled)
        print("      Delta scaled:", delta_scaled)

        # No need to wait: reading from the accelerometer takes long enough
    _ = input().strip()


def run_accelerometer_characterization_loop():
    accelerometer = ADXL375_Helper(XL3D_HARDWARE_OFFSET).accelerometer

    data_column_names = xl3d_format_characterization_header()
    while not supervisor.runtime.serial_bytes_available:
        # Any key to advance
        print()
        print("Monitoring accelerometer... press ENTER to run XL3D characterization scan.")
        print(data_column_names)
        xl3d_characterization_scan(accelerometer, samples_to_average=1)
        time.sleep(0.7)
    _ = input().strip()

    samples_to_average_list = [ 1,  2,  5, 10, 20, 50, 100, 200, 500, 1000, 2000]
    scan_count_list =         [30, 30, 30, 30, 30, 30,  30,  30,  20,   20,   20]
    print()
    print(data_column_names)
    for samples_to_average, repeat_count in zip(samples_to_average_list, scan_count_list):
        for _ in range(repeat_count):
            xl3d_characterization_scan(accelerometer, samples_to_average)

    print()
    print("Scan complete. Press ENTER to exit.")
    while not supervisor.runtime.serial_bytes_available:
        # Any key to advance
        time.sleep(0.7)
    _ = input().strip()


qtpys3_pin_list()

#run_accelerometer_offset_loop()
#run_accelerometer_self_test_loop()
#run_accelerometer_characterization_loop()
#run_analog_input_characterization_loop()

run_sensor_scan_loop()
