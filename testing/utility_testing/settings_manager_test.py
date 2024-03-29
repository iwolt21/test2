import unittest
import tempfile
import shutil
import os
import json
from src.utility.settings_manager import Settings

class TestSettingsManager(unittest.TestCase):
    temp_dir = None
    default_settings = None
    settings_path = None

    @classmethod
    def setUpClass(self):
        # Create a temporary directory for the settings file
        self.temp_dir = tempfile.mkdtemp()
        self.settings_path = os.path.join(self.temp_dir, 'settings.json')
        self.default_settings = {
            "language": "English",
            "institution": "Initial University",
            "CRKN_url": "https://initial-url.com",
            "CRKN_root_url": "https://initial-url.com",
            "CRKN_institutions": [],
            "local_institutions": [],
            "database_name": "initial_database.db",
            "github_link": "https://github.com/initial"
        }

        # Save default settings to the temporary settings.json file
        with open(self.settings_path, 'w') as file:
            json.dump(self.default_settings, file)

    @classmethod
    def tearDownClass(cls):
        # Remove the temporary directory after the tests
        shutil.rmtree(cls.temp_dir)

    def test_singleton_behavior(self):
        instance_one = Settings(self.settings_path)
        instance_two = Settings(self.settings_path)
        self.assertIs(instance_one, instance_two, "SettingsManager does not enforce singleton behavior")

    def test_load_settings_successfully(self):
        settings_manager = Settings(self.settings_path)
        for key, expected_value in self.default_settings.items():
            self.assertEqual(settings_manager.get_setting(key), expected_value, f"Failed to load {key} correctly")

    def test_handle_missing_settings_json(self):
        os.remove(self.settings_path)  # Ensure settings.json is missing
        settings_manager = Settings(self.settings_path)
        self.assertIsNotNone(settings_manager, "SettingsManager failed to handle missing settings.json")

    def test_update_setting(self):
        new_language = "French"
        settings_manager = Settings(self.settings_path)
        settings_manager.update_setting("language", new_language)
        with open(self.settings_path, 'r') as file:
            updated_settings = json.load(file)
        self.assertEqual(updated_settings["language"], new_language, "Failed to update setting in settings.json")

    def test_get_setting_value(self):
        settings_manager = Settings(self.settings_path)
        self.assertEqual(settings_manager.get_setting("language"), self.default_settings["language"], "Failed to retrieve the correct setting value")
