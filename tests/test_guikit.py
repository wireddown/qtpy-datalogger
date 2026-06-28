"""Tests for the guikit module."""

import tkinter as tk

from qtpy_datalogger import guikit


def test_can_use_font_awesome_icons() -> None:
    """Do the custom overrides for ttkbootstrap_icons succeed?"""
    _ = tk.Tk()
    _ = guikit.image_from_icon("worm")
