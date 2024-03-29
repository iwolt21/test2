from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QTextEdit, QComboBox, QWidget
from src.utility.export import export_data
from src.utility.settings_manager import Settings
from PyQt6.QtCore import Qt
import os


settings_manager = Settings()


# this class defines the search page please add the search page code here
class searchDisplay(QDialog):
    _instance = None
    @classmethod
    def get_instance(cls, arg1, arg2):
        if not cls._instance:
            cls._instance = cls(arg1, arg2)
        return cls._instance
    
    @classmethod
    def replace_instance(cls, arg1, arg2):
        if cls._instance:
            # Remove the previous instance's reference from its parent widget
            cls._instance.setParent(None)
            # Explicitly delete the previous instance
            del cls._instance
            print("Deleting instance")
        cls._instance = cls(arg1, arg2)
        return cls._instance

    def __init__(self, widget, results):
        super(searchDisplay, self).__init__()
        language_value = settings_manager.get_setting("language").lower()
        ui_file = os.path.join(os.path.dirname(__file__), f"{language_value}_searchDisplay.ui")
        loadUi(ui_file, self)

        # this is the back button that will take to the startscreen from the searchdisplay
        self.backButton.clicked.connect(self.backToStartScreen)
        self.exportButton.clicked.connect(self.export_data_handler)
        self.widget = widget
        self.results = results
        self.original_widget_values = None
        self.column_labels = ["Access", "File_Name", "Platform", "Title", "Publisher", "Platform_YOP", "Platform_eISBN", "OCN", "agreement_code", "collection_name", "title_metadata_last_modified"]

        self.tableWidget.itemSelectionChanged.connect(self.updateCellNameDisplay)

        self.display_results_in_table()

    # using this method to show the results of the clicked cell on the top of the page whenever clicked on cell.
    def updateCellNameDisplay(self):
        selected_items = self.tableWidget.selectedItems()
        if selected_items:
            text = selected_items[0].text()
            self.cellName.setText(text)
        else:
            self.cellName.setText("No cell selected")


    def backToStartScreen(self):
        self.widget.removeWidget(self.widget.currentWidget())


    def display_results_in_table(self):
        self.tableWidget.setRowCount(0) 
        self.tableWidget.setColumnCount(len(self.results[0])) if self.results else self.tableWidget.setColumnCount(0)

        if self.results:
            self.tableWidget.setHorizontalHeaderLabels(self.column_labels)

        for row_number, row_data in enumerate(self.results):
            self.tableWidget.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                self.tableWidget.setItem(row_number, column_number, QTableWidgetItem(str(data)))

    def export_data_handler(self):
        export_data(self.results, self.column_labels)

    def update_all_sizes(self):
        original_width = 1200
        original_height = 800
        new_width = self.width() + 25
        new_height = self.height()

        if self.original_widget_values is None:
            # If it's the first run, store the original values
            self.original_widget_values = {}
            for widget in self.findChildren(QWidget):
                self.original_widget_values[widget] = {
                    'geometry': widget.geometry(),
                    'font_size': widget.font().pointSize() if isinstance(widget, (QTextEdit, QComboBox)) else None
                }

        # Iterate through every widget loaded using loadUi
        for widget, original_values in self.original_widget_values.items():
            # Calculate new geometry and size for each widget
            x = int(original_values['geometry'].x() * (new_width / original_width))
            y = int(original_values['geometry'].y() * (new_height / original_height))
            width = int(original_values['geometry'].width() * (new_width / original_width))
            height = int(original_values['geometry'].height() * (new_height / original_height))

            # Set the new geometry and size
            widget.setGeometry(x, y, width, height)

            # If the widget is a QTextEdit or QComboBox, adjust font size
            if isinstance(widget, (QTextEdit, QComboBox)):
                font = widget.font()
                original_font_size = original_values['font_size']
                if original_font_size is not None:
                    font.setPointSize(int(original_font_size * (new_width / original_width)))
                widget.setFont(font)
        
        self.tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        table_width = int(0.8 * new_width)
        self.tableWidget.setFixedWidth(table_width)

        # Calculate the width for each column
        num_columns = self.tableWidget.columnCount()
        column_width = (self.tableWidget.viewport().width()) // num_columns if num_columns > 0 else 0

        # Set the calculated width for each column
        for column_number in range(num_columns):
            self.tableWidget.setColumnWidth(column_number, column_width)

    def resizeEvent(self, event):
        # Override the resizeEvent method to call update_all_sizes when the window is resized
        super().resizeEvent(event)
        self.update_all_sizes()

    def keyPressEvent(self, event):
        # Override keyPressEvent method to ignore Escape key event
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()  # Ignore the Escape key event
        else:
            super().keyPressEvent(event)
