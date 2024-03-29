from PyQt6.QtWidgets import QDialog, QPushButton, QLabel, QInputDialog, QFrame, QMessageBox
from PyQt6.uic import loadUi
from src.utility.upload import upload_and_process_file
from src.data_processing.database import get_local_tables, connect_to_database, close_database, get_table_data
from src.utility.settings_manager import Settings
import os

settings_manager = Settings()

class ManageInstitutionsPopup(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language_value = settings_manager.get_setting("language")
        self.setWindowTitle("Manage Institutions" if self.language_value == "English" else "Gérer les établissements")
    
        ui_file = os.path.join(os.path.dirname(__file__), f"{self.language_value.lower()}_manageInstitution.ui")
        loadUi(ui_file, self) 

        self.uploadButton = self.findChild(QPushButton, 'uploadButton')
        self.uploadButton.clicked.connect(self.upload_local_institution)
                
        self.populate_table_information()  # Populate the table information initially
        
    def populate_table_information(self):
        self.deleteTableData()
        
        # Get those tables
        connection = connect_to_database()
        institutions = settings_manager.get_setting("local_institutions")

        # Populate the scroll area with table information
        for institution in institutions:
            table_label = QLabel(f"{institution}")
            
            remove_button = QPushButton("Remove" if self.language_value == "English" else "Retirer")
            remove_button.clicked.connect(lambda checked, institution=institution: self.remove_institution(institution))

            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)

            # Add the horizontal layout to the main vertical layout
            self.scrollLayout.addWidget(table_label)
            self.scrollLayout.addWidget(remove_button)
            self.scrollLayout.addWidget(line)
        
        close_database(connection)

        
    def remove_institution(self, institution):
        from src.utility.upload import remove_local_file
        confirm = QMessageBox.question(self, "Confirmation", 
                                       f"Are you sure you want to remove {institution}?" if self.language_value == "English" else f"Êtes-vous sûr de vouloir supprimer {institution}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            print(institution)
            settings_manager.remove_local_institution(institution)
            self.populate_table_information() 
            QMessageBox.information(self, "Success" if self.language_value == "English" else "Succès", 
                                    f"{institution} has been removed successfully." if self.language_value == "English" else f"{institution} a été supprimé avec succès.")
            
    def deleteTableData(self):
        for i in reversed(range(self.scrollLayout.count())):
            item = self.scrollLayout.itemAt(i)
            if (item is not None):
                widget = item.widget()
                if (widget is not None):
                    self.scrollLayout.removeWidget(widget) 
                    widget.setParent(None)
                    widget.deleteLater()

    def upload_local_institution(self):
        institution, ok_pressed = QInputDialog.getText(self, "Add Institution" if self.language_value == "English" else "Ajouter un établissement", 
                                                       "Enter institution name:" if self.language_value == "English" else "Entrez le nom de l'établissement :")
        if ok_pressed and institution.strip() and institution not in settings_manager.get_setting("local_institutions"): 
            settings_manager.add_local_institution(institution)
            self.populate_table_information()
        elif institution in settings_manager.get_institutions():
            QMessageBox.warning(self, "Warning" if self.language_value == "English" else "Avertissement", 
                                "Institution already saved." if self.language_value == "English" else "Établissement déjà enregistré.")
        else:
            QMessageBox.warning(self, "Warning" if self.language_value == "English" else "Avertissement", 
                                "No institution name entered or input is empty." if self.language_value == "English" else "Aucun nom d'institution saisi ou la saisie est vide.")
