from PyQt6.QtWidgets import QDialog, QPushButton, QLabel, QFrame, QMessageBox
from PyQt6.uic import loadUi
from src.utility.upload import upload_and_process_file
from src.data_processing.database import get_local_tables, connect_to_database, close_database, get_table_data
from src.utility.settings_manager import Settings
import os

settings_manager = Settings()

class ManageLocalDatabasesPopup(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language_value = settings_manager.get_setting("language")
        self.setWindowTitle("Manage Local Databases" if self.language_value == "English" else "Gérer les bases de données locales")
    
        ui_file = os.path.join(os.path.dirname(__file__), f"{self.language_value.lower()}_manageDatabase.ui")
        loadUi(ui_file, self) 

        self.uploadButton = self.findChild(QPushButton, 'uploadButton')
        self.uploadButton.clicked.connect(self.upload_local_databases)
                
        self.populate_table_information()  # Populate the table information initially
        
    def populate_table_information(self):
        self.deleteTableData()
        
        # Get those tables
        connection = connect_to_database()
        local_table_data = get_table_data(connection, "local_file_names")

        print(local_table_data)

        # Populate the scroll area with table information
        for table_data in local_table_data:
            table_label = QLabel(f"{table_data[0]}, \n{'Date Added' if self.language_value == 'English' else 'Date ajoutée'}: {table_data[1]}")
            
            remove_button = QPushButton("Remove" if self.language_value == "English" else "Retirer")
            remove_button.clicked.connect(lambda checked, table=table_data[0]: self.remove_table(table))

            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            
            # Create a horizontal layout for each row
            # row_layout = QVBoxLayout()
            # row_layout.addWidget(table_label)
            # row_layout.addWidget(remove_button)
            # row_layout.addWidget(line)

            # Add the horizontal layout to the main vertical layout
            self.scrollLayout.addWidget(table_label)
            self.scrollLayout.addWidget(remove_button)
            self.scrollLayout.addWidget(line)
        
        close_database(connection)

    def remove_table(self, table_name):
        from src.utility.upload import remove_local_file
        confirm = QMessageBox.question(self, "Confirmation", 
                                       f"Are you sure you want to remove {table_name}?" if self.language_value == "English" else f"Êtes-vous sûr de vouloir supprimer {table_name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            remove_local_file(table_name.lstrip("local_"))
            self.populate_table_information() 
            QMessageBox.information(self, "Success" if self.language_value == "English" else "Succès", 
                                    f"{table_name} has been removed successfully." if self.language_value == "English" else f"{table_name} a été supprimé avec succès.")
            
    def deleteTableData(self):
        for i in reversed(range(self.scrollLayout.count())):
            item = self.scrollLayout.itemAt(i)
            if (item is not None):
                widget = item.widget()
                if (widget is not None):
                    self.scrollLayout.removeWidget(widget) 
                    widget.setParent(None)
                    widget.deleteLater()

    def upload_local_databases(self):
        upload_and_process_file()
        self.populate_table_information()