import json
import os


'''
Baki Feb 26

Interaction with the settings.json file goes through this settings_manager.py. Need to make an instance of
settings_manager first to get or update values like this:
1) import settings 
from src.utility.settings_manager import Settings
2) create a global instance
settings_manager = Settings()
3) use any of the functionalities through settings_manager for example:
settings_manager.update_setting('CRKN_url', new_url)


To check the current applied setting use get_setting method and pass the key
settings_manager.get_setting('institution')

'''


class SingletonMeta(type):
    """
    A Singleton metaclass that creates a single instance of a class.
    """

    # Dictionary to check if a class already has an instance created
    _instances = {}

    # Checks for an existing instance before creating a new one
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Settings(metaclass=SingletonMeta):
    """
        Settings Manager class that uses the Singleton pattern to ensure that only
        one instance manages the application settings.
        """

    def __init__(self, settings_file=None):
        if not hasattr(self, 'initialized'):  # Avoid reinitialization
            if settings_file is None:
                settings_file = f"{os.path.abspath(os.path.dirname(__file__))}/settings.json"
            self.settings_file = settings_file
            self.settings = self.load_settings()
            self.initialized = True

    def load_settings(self):
        """Load the current settings from the JSON file."""
        try:
            with open(self.settings_file, 'r') as file:
                settings = json.load(file)
        except FileNotFoundError:
            # Write default settings to a new settings.json
            default_db_path = os.path.join(os.path.dirname(self.settings_file), 'ebook_database.db')
            settings = {
                "language": "English",
                "allow_CRKN": "True",
                "institution": "Univ. of Prince Edward Island",
                "CRKN_url": "https://library.upei.ca/test-page-ebooks-perpetual-access-project",
                "CRKN_root_url": "https://library.upei.ca",
                "CRKN_institutions": [],
                "local_institutions": [],
                "database_name": default_db_path,
                "github_link": "https://github.com/eppenney/eBook-Perpetual-Access-Rights-Tracker"
            }
            # Set the CRKN root url from the CRKN url
            url_parts = settings["CRKN_url"].split('/')
            settings["CRKN_root_url"] = '/'.join(url_parts[:3])
        return settings

    def save_settings(self):
        """Save the current settings back to the JSON file."""
        with open(self.settings_file, 'w') as file:
            json.dump(self.settings, file, indent=4)

    def update_setting(self, key, value):
        """
        Update a specific setting and save the change.
        :param key: setting key to update
        :param value: value for new setting
        """
        self.settings[key] = value
        self.save_settings()

    def get_setting(self, key):
        """
        Retrieve a specific setting's value.
        :param key: setting to get
        :return: value of that setting
        """
        return self.settings.get(key, None)

    def set_language(self, language):
        """
        Set the application language.
        :param language: new language
        """
        self.update_setting('language', language)

    def set_allow_CRKN(self, allowCRKN):
        """
        Allow to use CRKN.
        :param allowCRKN: "True" or "False"
        """
        self.update_setting('allow_CRKN', allowCRKN)

    def set_crkn_url(self, url):
        """
        Set the CRKN URL.
        :param url: new url
        """
        self.update_setting('CRKN_url', url)
        self.settings["CRKN_root_url"] = "/".join(url.split("/")[:3])
        self.save_settings()

    def set_github_link(self, link):
        """
        Set the GitHub link for the project.
        :param link: new link
        """
        self.update_setting('github_link', link)

    def set_institution(self, institution):
        """
        Set the institution.
        :param institution: new institution
        """
        self.update_setting('institution', institution)

    def add_local_institution(self, institution):
        """
        Add institution to local list.
        :param institution: new institution
        """
        self.settings["local_institutions"].append(institution)
        self.save_settings()

    def remove_local_institution(self, institution):
        """
        Remove institution from local list.
        :param institution: institution to remove
        """
        try:
            self.settings["local_institutions"].remove(institution)
            self.save_settings()
        except ValueError:
            pass

    def set_CRKN_institutions(self, institutions):
        """
        Add CRKN institutions to CRKN_institutions if they are not already in it.
        :param institutions: list of CRKN institutions from CRKN file
        """
        self.update_setting("CRKN_institutions", institutions)

    def get_institutions(self):
        """
        Get combined list of CRKN and local institutions
        :return: list - containing CRKN_institutions and local_institutions
        """
        return self.settings.get("local_institutions") + self.settings.get("CRKN_institutions")
    