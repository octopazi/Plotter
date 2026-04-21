import os

from PyQt5.QtCore import QSettings


class AppSettings:
    """Thin wrapper around QSettings for small persisted UI state."""

    ORGANIZATION = "Plotter"
    APPLICATION = "Plotter"

    @classmethod
    def _settings(cls):
        return QSettings(cls.ORGANIZATION, cls.APPLICATION)

    @classmethod
    def get_value(cls, key, default_value="", value_type=str):
        return cls._settings().value(key, default_value, type=value_type)

    @classmethod
    def set_value(cls, key, value):
        cls._settings().setValue(key, value)

    @classmethod
    def get_directory(cls, key, default_directory=""):
        return cls.get_value(key, default_directory, str)

    @classmethod
    def remember_directory_from_paths(cls, key, paths):
        if not paths:
            return

        directory = os.path.dirname(paths[0])
        if directory:
            cls.set_value(key, directory)

    @classmethod
    def restore_combo_selection(cls, combo_box, key):
        saved_value = cls.get_value(key, "", str)
        if not saved_value:
            return

        index = combo_box.findText(saved_value)
        if index >= 0:
            combo_box.setCurrentIndex(index)

    @classmethod
    def save_combo_selection(cls, combo_box, key):
        cls.set_value(key, combo_box.currentText())

    @classmethod
    def get_item_index(cls, key, items, default_index=0):
        saved_value = cls.get_value(key, "", str)
        if saved_value in items:
            return items.index(saved_value)
        return default_index