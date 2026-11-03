"""Unified command-line entry point for the THz scanning stage.

Edit ``CONFIG`` below for a new experiment.  The existing standalone scripts
remain available, while this file provides one menu for origin reset, full
WASD stage control, and a complete scan followed immediately by plotting.
"""

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
import msvcrt

import pyvisa

import plot_scan
import return_origin as origin_module
import scan_top
from pyMcc import MoCtrlCard
from return_origin import return_to_origin


@dataclass
class Settings:
    # Motion controller and axis mapping.
    motor_port: str = "COM5"
    x_axis_id: int = 0
    y_axis_id: int = 1
    x_origin: float = 5.000
    y_origin: float = 6.000
    x_origin_speed: float = 10.0
    y_origin_speed: float = 10.0

    # Scan grid and motion parameters.
    x_points: int = 75
    y_points: int = 125
    x_step_distance: float = 0.4
    y_step_distance: float = 0.4
    velocity: float = 10.0
    acceleration: float = 0.0
    move_timeout: float = 60.0
    poll_interval: float = 0.2
    status_query_retries: int = 3
    status_query_retry_delay: float = 0.3
    settle_time: float = 0.5
    origin_timeout: float = 120.0
    return_to_origin_before_scan: bool = True

    # Spectrum analyzer and output.
    visa_address: str = "TCPIP0::192.168.31.14::5025::SOCKET"
    visa_timeout_ms: int = 10000
    output_directory: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "img_output"
    )
    plot_percentiles: tuple = (2.0, 98.0)
    plot_platform_coordinates: bool = False

    # Single-move mode uses these defaults when distance is left blank.
    manual_x_step_distance: float = 1.0
    manual_y_step_distance: float = 1.0
    manual_velocity: float = 5.0
    manual_acceleration: float = 0.0


# This is the one configuration block used by every mode.
CONFIG = Settings()
AXIS_NAMES = {CONFIG.x_axis_id: "X", CONFIG.y_axis_id: "Y"}


def configure_scan_module(settings):
    """Apply unified settings to the unchanged scan implementation."""
    values = {
        "MOTOR_PORT": settings.motor_port,
        "X_POINTS": settings.x_points,
        "Y_POINTS": settings.y_points,
        "X_STEP_DISTANCE": settings.x_step_distance,
        "Y_STEP_DISTANCE": settings.y_step_distance,
        "VELOCITY": settings.velocity,
        "ACCELERATION": settings.acceleration,
        "MOVE_TIMEOUT": settings.move_timeout,
        "POLL_INTERVAL": settings.poll_interval,
        "STATUS_QUERY_RETRIES": settings.status_query_retries,
        "STATUS_QUERY_RETRY_DELAY": settings.status_query_retry_delay,
        "SETTLE_TIME": settings.settle_time,
        "ORIGIN_TIMEOUT": settings.origin_timeout,
        "VISA_ADDRESS": settings.visa_address,
        "VISA_TIMEOUT_MS": settings.visa_timeout_ms,
        "OUTPUT_DIRECTORY": settings.output_directory,
        "X_AXIS_ID": settings.x_axis_id,
        "Y_AXIS_ID": settings.y_axis_id,
    }
    for name, value in values.items():
        setattr(scan_top, name, value)
    scan_top.AXIS_NAMES = {
        settings.x_axis_id: "X",
        settings.y_axis_id: "Y",
    }


def require_ok(card, result, operation):
    if result != card.FUNRESOK:
        raise RuntimeError("{} failed (controller result: {}).".format(operation, result))


def move_and_wait(card, axis_id, distance, velocity, acceleration, settings):
    """Move one axis by a relative distance and wait for completion."""
    axis_name = AXIS_NAMES.get(axis_id, str(axis_id))
    result = card.MoCtrCard_MCrlAxisRelMove(
        axis_id, distance, velocity, acceleration
    )
    require_ok(card, result, "Move command for {} axis".format(axis_name))
    start_time = time.monotonic()
    try:
        while True:
            result, running = card.MoCtrCard_IsAxisRunning(axis_id)
            require_ok(card, result, "Read {} axis running state".format(axis_name))
            if not running:
                break
            if time.monotonic() - start_time >= settings.move_timeout:
                raise TimeoutError(
                    "{} axis did not finish within {:.1f} seconds.".format(
                        axis_name, settings.move_timeout
                    )
                )
            time.sleep(settings.poll_interval)
    except BaseException:
        stop_result = card.MoCtrCard_EmergencyStopAxisMov(axis_id)
        if stop_result != card.FUNRESOK:
            print("Emergency stop failed (controller result: {}).".format(stop_result))
        raise

    result, position = card.MoCtrCard_GetAxisPos(axis_id)
    require_ok(card, result, "Read {} axis position".format(axis_name))
    print("{} position: {:.4f}".format(axis_name, position[0]))


def initialize_card(settings):
    card = MoCtrlCard()
    result = card.MoCtrCard_Initial(settings.motor_port)
    require_ok(card, result, "Initialize motion controller")
    return card


def run_origin_mode(settings):
    # ``return_origin.py`` keeps its target coordinates as module settings;
    # assign them here so every mode uses the same unified configuration.
    origin_module.ORIGIN_X = settings.x_origin
    origin_module.ORIGIN_Y = settings.y_origin
    origin_module.AXIS_X = settings.x_axis_id
    origin_module.AXIS_Y = settings.y_axis_id
    print("Returning stage to the configured XY origin.")
    success = return_to_origin(
        com_port=settings.motor_port,
        x_speed=settings.x_origin_speed,
        y_speed=settings.y_origin_speed,
        timeout=settings.origin_timeout,
        confirm=True,
        verbose=True,
    )
    if not success:
        raise RuntimeError("Could not return the stage to the configured origin.")


def read_manual_key(settings):
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            return key.lower()
        time.sleep(settings.poll_interval)


def stop_axis(card, axis_id):
    axis_name = AXIS_NAMES.get(axis_id, str(axis_id))
    result = card.MoCtrCard_EmergencyStopAxisMov(axis_id)
    if result != card.FUNRESOK:
        print(
            "Emergency stop failed for {} axis (controller result: {}).".format(
                axis_name, result
            )
        )


def check_axis_idle(card, axis_id, operation):
    axis_name = AXIS_NAMES.get(axis_id, str(axis_id))
    result, running = card.MoCtrCard_IsAxisRunning(axis_id)
    require_ok(card, result, "Read {} axis state".format(axis_name))
    if running:
        raise RuntimeError(
            "{} axis is already moving; refusing to start {}.".format(
                axis_name, operation
            )
        )
    result, position = card.MoCtrCard_GetAxisPos(axis_id)
    require_ok(card, result, "Read {} axis position".format(axis_name))
    print("{} position: {:.4f}".format(axis_name, position[0]))


def run_manual_mode(settings):
    """Run the complete WASD controller from ``manual_stage_control.py``."""
    card = MoCtrlCard()
    initialized = False
    try:
        available_ports = [
            port.device for port in card.MoCtrCard_GetAvailablePorts()
        ]
        if settings.motor_port not in available_ports:
            raise RuntimeError(
                "Configured motor port {} is not available (found: {}).".format(
                    settings.motor_port,
                    ", ".join(available_ports) if available_ports else "none",
                )
            )

        result = card.MoCtrCard_Initial(settings.motor_port)
        require_ok(card, result, "Initialize motion controller")
        initialized = True

        for axis_id in (settings.x_axis_id, settings.y_axis_id):
            check_axis_idle(card, axis_id, "manual control")

        key_moves = {
            "w": (settings.y_axis_id, settings.manual_y_step_distance),
            "s": (settings.y_axis_id, -settings.manual_y_step_distance),
            "a": (settings.x_axis_id, -settings.manual_x_step_distance),
            "d": (settings.x_axis_id, settings.manual_x_step_distance),
        }
        print(
            "W: Y+, S: Y-, A: X-, D: X+; Q: quit."
        )
        print(
            "Configured manual steps: X={:g}, Y={:g}; velocity={:g}.".format(
                settings.manual_x_step_distance,
                settings.manual_y_step_distance,
                settings.manual_velocity,
            )
        )
        print("Each key press moves one configured step.")
        print("Verify the stage direction, travel limits, and emergency stop.")
        if input("Type YES to enable keyboard control: ").strip() != "YES":
            print("Cancelled.")
            return

        while True:
            key = read_manual_key(settings)
            if key == "q":
                print("Manual control stopped.")
                return
            if key not in key_moves:
                continue
            axis_id, distance = key_moves[key]
            axis_name = AXIS_NAMES.get(axis_id, str(axis_id))
            print(
                "{}: moving {} axis by {:+g}.".format(
                    key.upper(), axis_name, distance
                )
            )
            move_and_wait(
                card,
                axis_id,
                distance,
                settings.manual_velocity,
                settings.manual_acceleration,
                settings,
            )
    except KeyboardInterrupt:
        print("\nInterrupted; stopping both XY axes.")
        if initialized:
            for axis_id in (settings.x_axis_id, settings.y_axis_id):
                stop_axis(card, axis_id)
        raise
    finally:
        if initialized:
            result = card.MoCtrCard_UnLoad()
            if result != card.FUNRESOK:
                print(
                    "Controller unload failed (controller result: {}).".format(result)
                )


def check_spectrum_analyzer(settings):
    """Check the configured VISA connection and report the instrument ID."""
    resource_manager = None
    instrument = None
    print("Checking spectrum analyzer connection...")
    try:
        resource_manager = pyvisa.ResourceManager("@py")
        instrument = cast(
            Any,
            resource_manager.open_resource(
                settings.visa_address, open_timeout=settings.visa_timeout_ms
            ),
        )
        instrument.timeout = settings.visa_timeout_ms
        instrument.read_termination = "\n"
        instrument.write_termination = "\n"
        instrument_id = instrument.query("*IDN?").strip()
        if not instrument_id:
            raise RuntimeError("The instrument returned an empty *IDN? response.")
        print("Spectrum analyzer: connected")
        print("  VISA address: {}".format(settings.visa_address))
        print("  *IDN?: {}".format(instrument_id))
    except Exception as exc:
        print("Spectrum analyzer: connection failed")
        print("  {}".format(exc))
    finally:
        if instrument is not None:
            try:
                instrument.close()
            except Exception as exc:
                print("  Warning: failed to close spectrum analyzer: {}".format(exc))
        if resource_manager is not None:
            try:
                resource_manager.close()
            except Exception as exc:
                print("  Warning: failed to close VISA resource manager: {}".format(exc))


def check_motor_controller(settings):
    """Check the configured COM connection and show the current XY position."""
    card = MoCtrlCard()
    initialized = False
    print("Checking motor controller connection...")
    try:
        available_ports = [
            port.device for port in card.MoCtrCard_GetAvailablePorts()
        ]
        if settings.motor_port not in available_ports:
            print("Motor controller: connection failed")
            print(
                "  Configured port {} is unavailable (found: {}).".format(
                    settings.motor_port,
                    ", ".join(available_ports) if available_ports else "none",
                )
            )
            return

        result = card.MoCtrCard_Initial(settings.motor_port)
        require_ok(card, result, "Initialize motion controller")
        initialized = True
        positions = {}
        for axis_id, axis_name in (
            (settings.x_axis_id, "X"),
            (settings.y_axis_id, "Y"),
        ):
            result, position = card.MoCtrCard_GetAxisPos(axis_id)
            require_ok(card, result, "Read {} axis position".format(axis_name))
            positions[axis_name] = position[0]

        print("Motor controller: connected")
        print("  COM port: {}".format(settings.motor_port))
        print("  X position: {:.6f}".format(positions["X"]))
        print("  Y position: {:.6f}".format(positions["Y"]))
    except Exception as exc:
        print("Motor controller: connection failed")
        print("  {}".format(exc))
    finally:
        if initialized:
            try:
                result = card.MoCtrCard_UnLoad()
                if result != card.FUNRESOK:
                    print(
                        "  Warning: controller unload failed (result: {}).".format(
                            result
                        )
                    )
            except Exception as exc:
                print("  Warning: failed to unload controller: {}".format(exc))


def run_scan_mode(settings):
    configure_scan_module(settings)
    os.makedirs(settings.output_directory, exist_ok=True)
    output_path = os.path.join(
        settings.output_directory,
        "scan_top_{}.csv".format(datetime.now().strftime("%Y%m%d_%H%M%S")),
    )
    resource_manager = None
    instrument = None
    card = MoCtrlCard()
    try:
        scan_top.validate_config(card)
        print("Connecting to spectrum analyzer.")
        resource_manager = pyvisa.ResourceManager("@py")
        # PyVISA's base ``Resource`` type omits these SCPI message-resource
        # attributes, although the object returned for this address supports
        # them at runtime.  The cast only informs the static type checker.
        instrument = cast(
            Any,
            resource_manager.open_resource(
                settings.visa_address, open_timeout=settings.visa_timeout_ms
            ),
        )
        instrument.timeout = settings.visa_timeout_ms
        instrument.read_termination = "\n"
        instrument.write_termination = "\n"

        if settings.return_to_origin_before_scan:
            run_origin_mode(settings)

        result = card.MoCtrCard_Initial(settings.motor_port)
        require_ok(card, result, "Initialize motor controller for scanning")
        print("Starting scan.")
        scan_top.run_scan(card, instrument, output_path)

        # The CSV is complete; create its image before returning to the menu.
        image_path = plot_scan.plot_scan(
            output_path,
            percentiles=settings.plot_percentiles,
            platform_coordinates=settings.plot_platform_coordinates,
        )
        print("Saved scan image to {}".format(image_path))
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


def print_menu():
    print("\nTHz imaging control")
    print("  1. Return to configured origin")
    print("  2. WASD manual stage control")
    print("  3. Scan and plot")
    print("  4. Check spectrum analyzer connection")
    print("  5. Check motor connection and XY position")
    print("  q. Quit")


def main():
    print("Unified THz imaging controller")
    print("Edit CONFIG in thz_imaging.py before connecting hardware.")
    while True:
        print_menu()
        choice = input("Select a mode: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            print("Exiting.")
            return
        try:
            if choice in ("1", "origin", "r"):
                run_origin_mode(CONFIG)
            elif choice in ("2", "manual", "move", "m"):
                run_manual_mode(CONFIG)
            elif choice in ("3", "scan", "s"):
                run_scan_mode(CONFIG)
            elif choice in ("4", "spectrum", "visa"):
                check_spectrum_analyzer(CONFIG)
            elif choice in ("5", "motor", "stage"):
                check_motor_controller(CONFIG)
            else:
                print("Unknown selection; choose 1, 2, 3, 4, 5, or q.")
        except KeyboardInterrupt:
            print("\nOperation interrupted.")
        except Exception as exc:
            print("Operation failed: {}".format(exc))


if __name__ == "__main__":
    main()
