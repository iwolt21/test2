"""
 This will act as the come page which will only open for the first time the application is opened.
 The settings saved from here will be saved for the first time.

"""
import os
from PyQt6.QtWidgets import QDialog, QComboBox, QPushButton, QLineEdit, QMessageBox
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.uic import loadUi
from src.utility.settings_manager import Settings

settings_manager = Settings()

class WelcomePage(QDialog):
    def __init__(self):
        super().__init__()
        self.language_value = settings_manager.get_setting("language").lower()
        ui_file = os.path.join(os.path.dirname(__file__), f"{self.language_value}_welcome_screen.ui")
        loadUi(ui_file, self)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)  # 1 second duration
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Populate institution selection combobox
        # Finding the combobox for the institution
        self.institutionSelection = self.findChild(QComboBox, 'institutionSelection')
        self.populate_institutions()
        self.set_institution(settings_manager.get_setting("institution"))

        # Populate language selection combobox
        # self.populate_languages()

        current_crkn_url = settings_manager.get_setting("CRKN_url")
        self.crknURL = self.findChild(QLineEdit, 'crknURL')
        self.crknURL.setText(current_crkn_url)

        # Connect save button click event
        self.saveButton = self.findChild(QPushButton, 'saveSettings')
        self.saveButton.clicked.connect(self.save_settings)

    def showEvent(self, event):
        # Override showEvent to start animation when the dialog is shown
        self.animation.setStartValue(0.0)  # Start with opacity 0
        self.animation.setEndValue(1.0)  # End with opacity 1
        self.animation.start()

    def populate_institutions(self):
        # Clear the existing items in the combo box
        self.institutionSelection.clear()
        # Get the list of institutions from the settings manager
        institutions = settings_manager.get_institutions()
        # Populate the combo box with institution names
        self.institutionSelection.addItems(institutions)

    def set_institution(self, institution_value):
        # Iterate over the items in the combo box
        for index in range(self.institutionSelection.count()):
            if self.institutionSelection.itemText(index) == institution_value:
                # Set the current index to the item that matches the desired value
                self.institutionSelection.setCurrentIndex(index)
                break

    # def populate_languages(self):
    #     # Populate the language selection combobox
    #     languageSelection = self.findChild(QComboBox, 'languageSetting')
    #     languageSelection.addItems(["English", "French"])

    def save_settings(self):
        # Get selected institution and language
        selected_institution = self.institutionSelection.currentText()
        selected_language = self.findChild(QComboBox, 'languageSetting').currentText()

        settings_manager.set_institution(selected_institution)
        settings_manager.set_language(selected_language)

        crkn_url = self.findChild(QLineEdit, 'crknURL').text()
        if len(crkn_url.split("/")) < 3:
            QMessageBox.warning(self, "Incorrect URL format",
                                "Incorrect URL format.\nEnsure URL begins with URL format, eg) http:// or https://.",
                                QMessageBox.StandardButton.Ok)
            return
        settings_manager.set_crkn_url(crkn_url)

        settings_manager.save_settings()

        # Close the come page
        self.accept()
