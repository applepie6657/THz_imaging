"""Scan a rectangular X/Y grid and save spectrum peak data to CSV."""

import csv
import os
import time
from datetime import datetime

import pyvisa
from pyMcc import MoCtrlCard
from return_origin import X_SPEED as ORIGIN_X_SPEED
from return_origin import Y_SPEED as ORIGIN_Y_SPEED
from return_origin import return_to_origin


# Adjust scan and connection parameters here before running.
MOTOR_PORT = "COM4"
X_POINTS = 30
Y_POINTS = 50
X_STEP_DISTANCE = 1.0  # Sign selects the direction.
Y_STEP_DISTANCE = 1.0  # Sign selects the direction.
VELOCITY = 10.0
ACCELERATION = 0.0  # 0 uses the acceleration configured in the controller.
MOVE_TIMEOUT = 60.0  # Seconds allowed for each motor move.
POLL_INTERVAL = 0.2  # Seconds between motor state queries.
RETURN_TO_ORIGIN = True
ORIGIN_TIMEOUT = 120.0  # Seconds allowed for each origin move.

VISA_ADDRESS = "TCPIP0::192.168.31.14::5025::SOCKET"
VISA_TIMEOUT_MS = 10000

OUTPUT_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img_output")
AXIS_NAMES = {0: "X", 1: "Y", 2: "Z", 3: "T"}
X_AXIS_ID = 0
Y_AXIS_ID = 1


def validate_config(card):
    if MOTOR_PORT not in [port.device for port in card.MoCtrCard_GetAvailablePorts()]:
        raise RuntimeError("Motor port {} is not available.".format(MOTOR_PORT))
    if X_POINTS < 1 or Y_POINTS < 1:
        raise ValueError("X_POINTS and Y_POINTS must be at least 1.")
    if X_STEP_DISTANCE == 0 or Y_STEP_DISTANCE == 0:
        raise ValueError("X_STEP_DISTANCE and Y_STEP_DISTANCE must not be 0.")
    if VELOCITY <= 0:
        raise ValueError("VELOCITY must be greater than 0.")
    if ACCELERATION < 0:
        raise ValueError("ACCELERATION must not be negative.")
    if MOVE_TIMEOUT <= 0 or POLL_INTERVAL <= 0:
        raise ValueError("MOVE_TIMEOUT and POLL_INTERVAL must be greater than 0.")
    if ORIGIN_TIMEOUT <= 0:
        raise ValueError("ORIGIN_TIMEOUT must be greater than 0.")
    if VISA_TIMEOUT_MS <= 0:
        raise ValueError("VISA_TIMEOUT_MS must be greater than 0.")


def require_ok(result, operation):
    if result != MoCtrlCard.FUNRESOK:
        raise RuntimeError("{} failed (controller result: {}).".format(operation, result))


def move_and_wait(card, axis_id, distance):
    result = card.MoCtrCard_MCrlAxisRelMove(
        axis_id, distance, VELOCITY, ACCELERATION
    )
    require_ok(result, "Motor move command")

    start_time = time.monotonic()
    try:
        while True:
            result, running = card.MoCtrCard_IsAxisRunning(axis_id)
            require_ok(result, "Read motor running state")
            if not running:
                return
            if time.monotonic() - start_time >= MOVE_TIMEOUT:
                raise TimeoutError(
                    "Motor did not finish within {:.1f} seconds.".format(MOVE_TIMEOUT)
                )
            time.sleep(POLL_INTERVAL)
    except BaseException:
        stop_result = card.MoCtrCard_EmergencyStopAxisMov(axis_id)
        if stop_result != MoCtrlCard.FUNRESOK:
            print("Error: emergency stop command failed (result: {}).".format(stop_result))
        raise


def read_peak(instrument):
    instrument.write("CALC:MARK1:TRAC 1")
    instrument.write("CALC:MARK1:MAX:PEAK")
    instrument.query("*OPC?")
    frequency_hz = float(instrument.query("CALC:MARK1:X?").strip())
    power_dbm = float(instrument.query("CALC:MARK1:Y?").strip())
    return frequency_hz, power_dbm


def run_scan(card, instrument, output_path):
    for axis_id in (X_AXIS_ID, Y_AXIS_ID):
        result, running = card.MoCtrCard_IsAxisRunning(axis_id)
        require_ok(result, "Read initial {} axis running state".format(AXIS_NAMES[axis_id]))
        if running:
            raise RuntimeError(
                "The {} axis is already moving; refusing to start.".format(
                    AXIS_NAMES[axis_id]
                )
            )

    instrument_id = instrument.query("*IDN?").strip()
    total_points = X_POINTS * Y_POINTS
    fieldnames = (
        "point",
        "row",
        "column",
        "timestamp",
        "x_position",
        "y_position",
        "x_step_distance",
        "y_step_distance",
        "velocity",
        "acceleration",
        "frequency_hz",
        "power_dbm",
        "instrument_id",
    )

    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        csv_file.flush()

        point = 0
        for row in range(Y_POINTS):
            x_direction = 1 if row % 2 == 0 else -1
            for column in range(X_POINTS):
                point += 1
                print(
                    "Measuring point {}/{} (row {}, column {}).".format(
                        point, total_points, row + 1, column + 1
                    )
                )

                result, x_position = card.MoCtrCard_GetAxisPos(X_AXIS_ID)
                require_ok(result, "Read X axis position")
                result, y_position = card.MoCtrCard_GetAxisPos(Y_AXIS_ID)
                require_ok(result, "Read Y axis position")
                frequency_hz, power_dbm = read_peak(instrument)

                writer.writerow(
                    {
                        "point": point,
                        "row": row + 1,
                        "column": column + 1,
                        "timestamp": datetime.now().astimezone().isoformat(),
                        "x_position": "{:.6f}".format(x_position[0]),
                        "y_position": "{:.6f}".format(y_position[0]),
                        "x_step_distance": X_STEP_DISTANCE,
                        "y_step_distance": Y_STEP_DISTANCE,
                        "velocity": VELOCITY,
                        "acceleration": ACCELERATION,
                        "frequency_hz": "{:.6f}".format(frequency_hz),
                        "power_dbm": "{:.6f}".format(power_dbm),
                        "instrument_id": instrument_id,
                    }
                )
                csv_file.flush()

                if column < X_POINTS - 1:
                    move_and_wait(
                        card, X_AXIS_ID, x_direction * X_STEP_DISTANCE
                    )

            if row < Y_POINTS - 1:
                move_and_wait(card, Y_AXIS_ID, Y_STEP_DISTANCE)

    print("Scan complete.")


def main():
    card = MoCtrlCard()
    resource_manager = None
    instrument = None

    try:
        validate_config(card)
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
        output_path = os.path.join(
            OUTPUT_DIRECTORY,
            "scan_top_{}.csv".format(datetime.now().strftime("%Y%m%d_%H%M%S")),
        )

        print("Connecting to spectrum analyzer.")
        resource_manager = pyvisa.ResourceManager("@py")
        instrument = resource_manager.open_resource(
            VISA_ADDRESS, open_timeout=VISA_TIMEOUT_MS
        )
        instrument.timeout = VISA_TIMEOUT_MS
        instrument.read_termination = "\n"
        instrument.write_termination = "\n"

        if RETURN_TO_ORIGIN:
            print("Returning stage to the configured default origin.")
            if not return_to_origin(
                com_port=MOTOR_PORT,
                x_speed=ORIGIN_X_SPEED,
                y_speed=ORIGIN_Y_SPEED,
                timeout=ORIGIN_TIMEOUT,
                confirm=False,
                verbose=False,
            ):
                raise RuntimeError("Could not return the stage to the configured origin.")

        print("Initializing motor controller for scanning.")
        result = card.MoCtrCard_Initial(MOTOR_PORT)
        require_ok(result, "Initialize motor controller for scanning")

        print("Starting scan.")
        run_scan(card, instrument, output_path)
    except Exception as exc:
        print("Scan failed: {}".format(exc))
        raise
    finally:
        try:
            if instrument is not None:
                instrument.close()
        finally:
            try:
                if resource_manager is not None:
                    resource_manager.close()
            finally:
                card.MoCtrCard_UnLoad()


if __name__ == "__main__":
    main()
