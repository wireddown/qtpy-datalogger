"""Tests for the guikit module."""

import tkinter as tk

import pytest

from qtpy_datalogger import guikit

SELECT_INT_WITH_INT = {
    1: 2,
    10: 1,
    100: 0,
}
SELECT_FLOAT_WITH_INT = {
    1: 0.1,
    10: 1.0,
    100: 10.0,
}
SELECT_STR_WITH_INT = {
    1: "min",
    10: "mid",
    100: "max",
}
SELECT_INT_WITH_FLOAT = {
    2.5: 2,
    20.5: 1,
    200.5: 0,
}
SELECT_FLOAT_WITH_FLOAT = {
    2.5: 0.1,
    20.5: 1.0,
    200.5: 10.0,
}
SELECT_STR_WITH_FLOAT = {
    2.5: "min",
    20.5: "mid",
    200.5: "max",
}


def test_can_use_font_awesome_icons() -> None:
    """Do the custom overrides for ttkbootstrap_icons succeed?"""
    _ = tk.Tk()
    _ = guikit.image_from_icon("worm")


def test_can_load_theme_catalog() -> None:
    """Does the ThemeCatalog load correctly?"""
    theme_catalog = guikit.ThemeCatalog.get_instance()

    assert theme_catalog.active_theme_key == "bootstrap-light"
    assert "Cosmo Dark" in theme_catalog.theme_names


def test_can_toggle_theme() -> None:
    """Does the ThemeChanger swap themes correctly?"""
    theme_catalog = guikit.ThemeCatalog.get_instance()
    assert theme_catalog.active_theme_key == "bootstrap-light"

    guikit.ThemeChanger.toggle_light_dark()

    assert theme_catalog.active_theme_key == "bootstrap-dark"


@pytest.mark.parametrize(
    ("upper_bound", "selection", "expected_selection"),
    [
        (3, SELECT_INT_WITH_INT, 2),
        (30, SELECT_FLOAT_WITH_INT, 1.0),
        (300, SELECT_STR_WITH_INT, "max"),
        (4.2, SELECT_INT_WITH_FLOAT, 2),
        (40.2, SELECT_FLOAT_WITH_FLOAT, 1.0),
        (400.2, SELECT_STR_WITH_FLOAT, "max"),
    ],
)
def test_get_first_in_range(
    upper_bound: guikit.SupportsFloat,
    selection: dict[guikit.ComparableNumeric, guikit.AnyType],
    expected_selection: guikit.AnyType,
) -> None:
    """Does get_first_in_range() select from dictionaries correctly?"""
    selected = guikit.get_first_in_range(upper_bound, selection)

    assert selected == expected_selection
