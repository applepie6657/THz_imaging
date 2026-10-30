"""Plot a scan CSV as a coordinate-aware power image."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REQUIRED_COLUMNS = ("x_position", "y_position", "power_dbm")


def load_scan_csv(csv_path):
    x_values = []
    y_values = []
    power_values = []
    x_step = None
    y_step = None

    with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header.")

        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(
                "CSV is missing required columns: {}.".format(
                    ", ".join(missing_columns)
                )
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                x_position = float(row["x_position"])
                y_position = float(row["y_position"])
                power_dbm = float(row["power_dbm"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Invalid coordinate or power value on CSV line {}.".format(
                        line_number
                    )
                ) from exc

            if not all(math.isfinite(value) for value in (x_position, y_position, power_dbm)):
                raise ValueError(
                    "Non-finite coordinate or power value on CSV line {}.".format(
                        line_number
                    )
                )

            x_values.append(x_position)
            y_values.append(y_position)
            power_values.append(power_dbm)

            if x_step is None and row.get("x_step_distance"):
                x_step = abs(float(row["x_step_distance"]))
            if y_step is None and row.get("y_step_distance"):
                y_step = abs(float(row["y_step_distance"]))

    if not power_values:
        raise ValueError("CSV contains no measurement rows.")

    return (
        np.asarray(x_values),
        np.asarray(y_values),
        np.asarray(power_values),
        x_step,
        y_step,
    )


def cell_edges(coordinates, fallback_step, axis_name):
    if len(coordinates) == 1:
        if fallback_step is None or fallback_step <= 0:
            raise ValueError(
                "Only one {} coordinate was found; a positive step distance "
                "is needed to determine the image extent.".format(axis_name)
            )
        half_step = fallback_step / 2.0
        return np.array(
            [coordinates[0] - half_step, coordinates[0] + half_step]
        )

    midpoints = (coordinates[:-1] + coordinates[1:]) / 2.0
    first_edge = coordinates[0] - (coordinates[1] - coordinates[0]) / 2.0
    last_edge = coordinates[-1] + (coordinates[-1] - coordinates[-2]) / 2.0
    return np.concatenate(([first_edge], midpoints, [last_edge]))


def plot_scan(csv_path, output_path=None, percentiles=(2.0, 98.0)):
    lower_percentile, upper_percentile = percentiles
    if not (0 <= lower_percentile < upper_percentile <= 100):
        raise ValueError("Percentiles must satisfy 0 <= low < high <= 100.")

    x_values, y_values, power_values, x_step, y_step = load_scan_csv(csv_path)

    # The scanner writes positions to six decimal places; rounding prevents
    # floating-point noise from creating duplicate grid coordinates.
    x_values = np.round(x_values, decimals=6)
    y_values = np.round(y_values, decimals=6)
    x_coordinates = np.unique(x_values)
    y_coordinates = np.unique(y_values)
    power_grid = np.full(
        (len(y_coordinates), len(x_coordinates)), np.nan, dtype=float
    )

    x_indices = {coordinate: index for index, coordinate in enumerate(x_coordinates)}
    y_indices = {coordinate: index for index, coordinate in enumerate(y_coordinates)}
    for x_position, y_position, power_dbm in zip(
        x_values, y_values, power_values
    ):
        row = y_indices[y_position]
        column = x_indices[x_position]
        if not np.isnan(power_grid[row, column]):
            raise ValueError(
                "CSV contains more than one measurement at "
                "X={:.6f}, Y={:.6f}.".format(x_position, y_position)
            )
        power_grid[row, column] = power_dbm

    lower_limit, upper_limit = np.percentile(
        power_values, [lower_percentile, upper_percentile]
    )
    if lower_limit == upper_limit:
        lower_limit -= 0.5
        upper_limit += 0.5

    masked_grid = np.ma.masked_invalid(power_grid)
    clipped_grid = np.ma.clip(masked_grid, lower_limit, upper_limit)
    extends = "both"
    if np.all(power_values >= lower_limit):
        extends = "max"
    if np.all(power_values <= upper_limit):
        extends = "min"
    if np.all((power_values >= lower_limit) & (power_values <= upper_limit)):
        extends = "neither"

    x_edges = cell_edges(x_coordinates, x_step, "X")
    y_edges = cell_edges(y_coordinates, y_step, "Y")
    figure, axes = plt.subplots(figsize=(8, 6), constrained_layout=True)
    image = axes.pcolormesh(
        x_edges,
        y_edges,
        clipped_grid,
        shading="flat",
        cmap="inferno",
        vmin=lower_limit,
        vmax=upper_limit,
    )
    colorbar = figure.colorbar(image, ax=axes, extend=extends)
    colorbar.set_label("Peak power (dBm)")
    axes.set_xlabel("X position (mm)")
    axes.set_ylabel("Y position (mm)")
    axes.set_title(Path(csv_path).stem)
    axes.set_aspect("equal", adjustable="box")
    axes.plot(
        x_values,
        y_values,
        color="white",
        linewidth=0.9,
        alpha=0.8,
        marker=".",
        markersize=3,
        label="Scan order",
        zorder=3,
    )
    axes.scatter(
        x_values[0],
        y_values[0],
        color="lime",
        edgecolors="black",
        s=42,
        label="Start",
        zorder=4,
    )
    axes.scatter(
        x_values[-1],
        y_values[-1],
        color="cyan",
        edgecolors="black",
        s=42,
        label="End",
        zorder=4,
    )
    axes.legend(loc="best")

    destination = (
        Path(output_path) if output_path else Path(csv_path).with_suffix(".png")
    )
    try:
        figure.savefig(destination, dpi=200)
    finally:
        plt.close(figure)
    return destination


def main():
    parser = argparse.ArgumentParser(
        description="Plot scan power in dBm over the measured X/Y coordinates."
    )
    parser.add_argument("csv_file", type=Path, help="Input scan CSV file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output image path (default: same name as the CSV with a .png suffix).",
    )
    parser.add_argument(
        "--percentiles",
        nargs=2,
        type=float,
        metavar=("LOW", "HIGH"),
        default=(2.0, 98.0),
        help="Color scale percentiles; default: 2 98.",
    )
    arguments = parser.parse_args()

    if not arguments.csv_file.is_file():
        parser.error("CSV file does not exist: {}".format(arguments.csv_file))

    try:
        output_path = plot_scan(
            arguments.csv_file,
            arguments.output,
            tuple(arguments.percentiles),
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print("Saved scan image to {}".format(output_path))


if __name__ == "__main__":
    main()
