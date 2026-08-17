"""Tests for the guikit module."""

import tkinter as tk

from qtpy_datalogger import guikit


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
