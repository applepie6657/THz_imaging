"""Use WASD key presses to move the XY stage by fixed increments."""

import msvcrt
import time

from pyMcc import MoCtrlCard


X_AXIS_ID = 0
Y_AXIS_ID = 1
X_STEP_DISTANCE = 1
Y_STEP_DISTANCE = 1
VELOCITY = 5.0
ACCELERATION = 0.0
MOVE_TIMEOUT = 60.0
POLL_INTERVAL = 0.1

KEY_MOVES = {
    "w": (Y_AXIS_ID, Y_STEP_DISTANCE),
    "s": (Y_AXIS_ID, -Y_STEP_DISTANCE),
    "a": (X_AXIS_ID, -X_STEP_DISTANCE),
    "d": (X_AXIS_ID, X_STEP_DISTANCE),
}
AXIS_NAMES = {X_AXIS_ID: "X", Y_AXIS_ID: "Y"}


def require_ok(card, result, operation):
    if result != card.FUNRESOK:
        raise RuntimeError("{} failed (controller result: {}).".format(operation, result))


def read_key():
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            return key.lower()
        time.sleep(POLL_INTERVAL)


def stop_axis(card, axis_id):
    result = card.MoCtrCard_EmergencyStopAxisMov(axis_id)
    if result != card.FUNRESOK:
        print(
            "Emergency stop failed for {} axis (controller result: {}).".format(
                AXIS_NAMES[axis_id], result
            )
        )


def move_and_wait(card, axis_id, distance):
    result = card.MoCtrCard_MCrlAxisRelMove(
        axis_id, distance, VELOCITY, ACCELERATION
    )
    require_ok(card, result, "Move command for {} axis".format(AXIS_NAMES[axis_id]))

    start_time = time.monotonic()
    try:
        while True:
            result, running = card.MoCtrCard_IsAxisRunning(axis_id)
            require_ok(
                card, result, "Read {} axis running state".format(AXIS_NAMES[axis_id])
            )
            if not running:
                break
            if time.monotonic() - start_time >= MOVE_TIMEOUT:
                raise TimeoutError(
                    "{} axis did not finish within {:.1f} seconds.".format(
                        AXIS_NAMES[axis_id], MOVE_TIMEOUT
                    )
                )
            time.sleep(POLL_INTERVAL)
    except BaseException:
        stop_axis(card, axis_id)
        raise

    result, position = card.MoCtrCard_GetAxisPos(axis_id)
    require_ok(card, result, "Read {} axis position".format(AXIS_NAMES[axis_id]))
    print("{} position: {:.4f}".format(AXIS_NAMES[axis_id], position[0]))


def run_control_loop(card, get_key):
    for axis_id in (X_AXIS_ID, Y_AXIS_ID):
        result, running = card.MoCtrCard_IsAxisRunning(axis_id)
        require_ok(
            card, result, "Read initial {} axis state".format(AXIS_NAMES[axis_id])
        )
        if running:
            raise RuntimeError(
                "{} axis is already moving; refusing to start.".format(
                    AXIS_NAMES[axis_id]
                )
            )
        result, position = card.MoCtrCard_GetAxisPos(axis_id)
        require_ok(
            card, result, "Read initial {} axis position".format(AXIS_NAMES[axis_id])
        )
        print("{} position: {:.4f}".format(AXIS_NAMES[axis_id], position[0]))

    print("W: Y+, S: Y-, A: X-, D: X+; Q: quit.")
    print("Each key press moves one configured step.")
    try:
        while True:
            key = get_key()
            if key == "q":
                print("Manual control stopped.")
                return
            if key not in KEY_MOVES:
                continue

            axis_id, distance = KEY_MOVES[key]
            print(
                "{}: moving {} axis by {:+g}.".format(
                    key.upper(), AXIS_NAMES[axis_id], distance
                )
            )
            move_and_wait(card, axis_id, distance)
    except KeyboardInterrupt:
        print("\nInterrupted; stopping both XY axes.")
        for axis_id in (X_AXIS_ID, Y_AXIS_ID):
            stop_axis(card, axis_id)
        raise


def main():
    card = MoCtrlCard()
    initialized = False
    try:
        ports = card.MoCtrCard_GetAvailablePorts()
        if not ports:
            raise RuntimeError("No serial ports found; check the controller connection.")

        print("Available serial ports:")
        for port in ports:
            print("  {}".format(port.device))
        com_port = input("Enter the controller COM port: ").strip()
        if com_port not in [port.device for port in ports]:
            raise ValueError("The selected port is not in the available port list.")

        result = card.MoCtrCard_Initial(com_port)
        require_ok(card, result, "Initialize motion controller")
        initialized = True
        print("Controller connected.")
        print(
            "Configured steps: X={:g}, Y={:g}; velocity={:g}.".format(
                X_STEP_DISTANCE, Y_STEP_DISTANCE, VELOCITY
            )
        )
        print("Verify the stage direction, travel limits, and emergency stop.")
        if input("Type YES to enable keyboard control: ").strip() != "YES":
            print("Cancelled.")
            return

        run_control_loop(card, read_key)
    except KeyboardInterrupt:
        print("\nControl cancelled.")
    except Exception as exc:
        print("Manual control failed: {}".format(exc))
        raise
    finally:
        if initialized:
            result = card.MoCtrCard_UnLoad()
            if result != card.FUNRESOK:
                print(
                    "Controller unload failed (controller result: {}).".format(result)
                )


if __name__ == "__main__":
    main()
