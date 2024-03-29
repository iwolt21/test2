import urllib

from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QDialog, QButtonGroup, QPushButton, QLineEdit, QMessageBox, QComboBox, QSizePolicy, QWidget, \
    QLabel
from PyQt6.QtGui import QIcon, QPixmap, QTransform, QFontMetrics, QDesktopServices
from src.user_interface.settingsPage import settingsPage
from src.data_processing.database import connect_to_database, \
    close_database, search_database
from src.utility.settings_manager import Settings
import os

"""
When creating instances of startScreen, use startScreen.get_instance(widget)
-Ethan
Feb 27, 2024
"""
settings_manager = Settings()

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))


class RotatableButton(QPushButton):
    def __init__(self, icon_path, settings_display_func, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(icon_path))
        self.setGeometry(15, 15, 50, 50)
        icon_size = self.size()
        self.setIconSize(icon_size)
        self.normal_icon = QIcon(icon_path)
        self.hover_icon = self.rotate_icon(icon_path, 15)  # Rotate the icon by 15 degrees
        self.clicked.connect(settings_display_func)
        self.setStyleSheet("border:none;")  # Remove button border

    def enterEvent(self, event):
        self.setIcon(self.hover_icon)  # Set rotated icon when mouse enters

    def leaveEvent(self, event):
        self.setIcon(self.normal_icon)  # Set normal icon when mouse leaves

    def rotate_icon(self, icon_path, degrees):
        pixmap = QPixmap(icon_path)
        transform = QTransform().rotate(degrees)
        rotated_pixmap = pixmap.transformed(transform)
        return QIcon(rotated_pixmap)

class startScreen(QDialog):
    _instance = None
    @classmethod
    def get_instance(cls, arg):
        if not cls._instance:
            cls._instance = cls(arg)
        return cls._instance
    
    @classmethod
    def replace_instance(cls, arg):
        cls._instance = cls(arg)
        return cls._instance
    
    def __init__(self, widget):
        super(startScreen, self).__init__()
        self.language_value = settings_manager.get_setting("language")
        ui_file = os.path.join(os.path.dirname(__file__), f"{self.language_value}_start.ui")  # Assuming the UI file is in the same directory as the script
        loadUi(ui_file, self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # settings up the internet connection in the icon at the end
        self.internetConnectionLabel = self.findChild(QLabel, 'internetConnection')
        self.updateConnectionStatus(False)

        # timer clock that will work with the Google time (Qtimer should be used)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkInternetConnection)
        self.timer.start(5000)

        # Basic idea we are going to do is stack here where each searchbar will be pop when the negative
        self.duplicateTextEdits = []
        self.duplicateCombos = []
        self.duplicateSearchTypes = []

        # Finding widgets
        self.textEdit = self.findChild(QLineEdit, 'textEdit')
        self.orLabel = self.findChild(QLabel, 'orLabel')
        self.booleanSearchType = self.findChild(QComboBox, 'booleanBoxRight')
        self.settingMenuButton = self.findChild(QPushButton, 'settingButton1')
        self.institutionButton = self.findChild(QPushButton, "institutionButton")
        self.textEdit.returnPressed.connect(self.search_button_clicked)
        self.institutionName = self.findChild(QLabel, "institutionName")

        # Clear Button
        self.clearButton = self.findChild(QPushButton, "clearButton")
        self.clearButton.clicked.connect(self.clearSearch)

        self.duplicateCount = 0
        self.orLabel.hide()

        # Add and remove field buttons:
        self.addFieldButton = self.findChild(QPushButton, 'pushButton')
        self.addFieldButton.clicked.connect(self.duplicateTextEdit)

        self.removeFieldButton = self.findChild(QPushButton, 'removeButton') #finding child pushButton from the parent class
        self.removeFieldButton.clicked.connect(self.removeTextEdit)

        self.search.clicked.connect(self.search_button_clicked)
        self.widget = widget  # Store the QStackedWidget reference

        self.helpIcon = self.findChild(QLabel, 'helpIcon')
        self.helpIcon.setPixmap(QPixmap('resources/helpIcon.png'))
        clickable_help_icon = ClickableLabel(self)
        clickable_help_icon.setGeometry(self.helpIcon.geometry())  # Match the geometry with the existing help icon

        clickable_help_icon.mousePressEvent = self.open_url  # Override the mousePressEvent

        # # making a group of different button to give a effect of burger menu
        self.buttonGroup = QButtonGroup()

        # # Settings
        # self.settingMenuButton.setIcon(QIcon("resources/Gear-icon.png"))
        # self.settingMenuButton.setGeometry(15, 15, self.settingMenuButton.width(), self.settingMenuButton.height())
        # icon_size = self.settingMenuButton.size()
        # self.settingMenuButton.setIconSize(icon_size)
        # self.settingMenuButton.clicked.connect(self.settingsDisplay)

        self.settingMenuButton = RotatableButton("resources/Gear-icon.png", self.settingsDisplay, self)
        self.settingMenuButton.clicked.connect(self.settingsDisplay)
        self.widget = widget

        self.displayInstitutionName()

        # Resizing Stuff
        self.original_widget_values = None 
        self.original_width = 1200
        self.original_height = 800
        self.new_width = 1200
        self.new_height = 800

        self.originalOffsetX = 20
        self.textOffsetX = 20
        self.textOffsetY = 10

        self.dupTextEdit = None

    def open_url(self, event):
        # Open the specified URL in the default web browser
        url = QUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        QDesktopServices.openUrl(url)

    # This is for this internet connection check and changes the color accordingly
    def checkInternetConnection(self):
        try:
            # Attempt to connect to a known host
            urllib.request.urlopen('http://google.com', timeout=1)
            self.updateConnectionStatus(True)
        except (urllib.error.URLError, OSError):
            # Catching both URLError and OSError
            self.updateConnectionStatus(False)

    def updateConnectionStatus(self, isConnected):
        if isConnected:
            self.internetConnectionLabel.setPixmap(QPixmap('resources/green_signal.png'))
            self.internetConnectionLabel.setToolTip("Internet Connection: Online")
        else:
            self.internetConnectionLabel.setPixmap(QPixmap('resources/red_signal.png'))
            self.internetConnectionLabel.setToolTip("Internet Connection: Offline")

    def displayInstitutionName(self):
        institution_name = settings_manager.get_setting('institution')
        if institution_name:
            self.institutionName.setText(institution_name)
        else:
            self.institutionName.setText(
                "No Institution Selected" if self.language_value == "English" else "Aucune institution sélectionnée")

        # Adjust label size dynamically based on text length
        font = self.institutionName.font()
        font_metrics = QFontMetrics(font)
        text_width = font_metrics.horizontalAdvance(institution_name)
        text_height = font_metrics.height()

        # Set the minimum size for the label based on the text size
        self.institutionName.setMinimumSize(text_width, text_height)

    # This method responsible for making the new text edit each time the plus sign is clicked.
    # Basically we are only having limit of 5 searches at the same time
    def duplicateTextEdit(self):
      if (self.dupTextEdit == None):
          self.dupTextEdit = self.newTextEdit()
      MAX_DUPLICATES = 5

      if self.duplicateCount < MAX_DUPLICATES:
        self.duplicateCount += 1  # Use the corrected attribute name

        new_text = self.newTextEdit()
        self.duplicateTextEdits.append(new_text) # this will store in the system making it like a stack that way we can pop through when negative
        new_text.show()
        

        new_and_or_box = self.newOrLabel()
        self.duplicateCombos.append(new_and_or_box)
        new_and_or_box.show()

        new_search_type = self.newBooleanSearchType()
        self.duplicateSearchTypes.append(new_search_type)
        new_search_type.show()

        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 1)
        self.addFieldButton.setGeometry(self.addFieldButton.x(), newY, self.addFieldButton.width(), self.addFieldButton.height())
        self.removeFieldButton.setGeometry(self.removeFieldButton.x(), newY, self.removeFieldButton.width(), self.removeFieldButton.height())

        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 2)
        self.search.setGeometry(self.search.x(), newY, self.search.width(), self.search.height())

        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 3)
        self.clearButton.setGeometry(self.clearButton.x(), newY, self.clearButton.width(), self.clearButton.height())

      else:
          QMessageBox.warning(self, "Limit reached" if self.language_value == "English" else "Limite atteinte", f"You can only search {MAX_DUPLICATES+1} at a time" if self.language_value == "English" else f"Vous ne pouvez rechercher que {MAX_DUPLICATES+1} à la fois.")

    def adjustDuplicateTextEditSize(self):
        for i in range(len(self.duplicateTextEdits)):
            newY = self.dupTextEdit.y() + (self.dupTextEdit.height() + self.textOffsetY) * (i + 1)
            self.duplicateTextEdits[i].setGeometry(self.dupTextEdit.x() - self.textOffsetX , newY, self.dupTextEdit.width(), self.dupTextEdit.height())
        for i in range(len(self.duplicateCombos)):
            newY = self.orLabel.y() + (self.orLabel.height() + self.textOffsetY) * (i + 1)
            self.duplicateCombos[i].setGeometry(self.orLabel.x(), newY, self.orLabel.width(), self.orLabel.height())
        for i in range(len(self.duplicateSearchTypes)):
            newY = self.booleanSearchType.y() + (self.booleanSearchType.height() + self.textOffsetY) * (i + 1)
            self.duplicateSearchTypes[i].setGeometry(self.booleanSearchType.x() - self.textOffsetX , newY, self.booleanSearchType.width(), self.booleanSearchType.height())
        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 1)
        self.addFieldButton.setGeometry(self.addFieldButton.x(), newY, self.addFieldButton.width(), self.addFieldButton.height())
        self.removeFieldButton.setGeometry(self.removeFieldButton.x(), newY, self.removeFieldButton.width(), self.removeFieldButton.height())
        
        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 2)
        self.search.setGeometry(self.search.x(), newY, self.search.width(), self.search.height())

        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 3)
        self.clearButton.setGeometry(self.clearButton.x(), newY, self.clearButton.width(), self.clearButton.height())
        

    def newTextEdit(self):
        new_text_edit = QLineEdit(self)
        newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * self.duplicateCount

        # Copy properties from the original textEdit
        new_text_edit.setFont(self.textEdit.font())
        new_text_edit.setStyleSheet(self.textEdit.styleSheet())

        # Set geometry for the new QLineEdit        
        new_text_edit.setGeometry(self.textEdit.x() + self.orLabel.width() , newY, self.textEdit.width() - self.orLabel.width() - self.textOffsetX, self.textEdit.height())
        
        # If there's any specific initialization content or placeholder text
        new_text_edit.setPlaceholderText(self.textEdit.placeholderText())
    
        self.original_widget_values[new_text_edit] = {
            'geometry': new_text_edit.geometry(),
            'font_size': new_text_edit.font().pointSize() if isinstance(new_text_edit, (QLineEdit, QComboBox)) else None
        }

        return new_text_edit
    
    def newOrLabel(self):
        newY = self.orLabel.y() + (self.orLabel.height() + self.textOffsetY) * self.duplicateCount

        # Duplicating the QComboBox when the text editor is duplicated.
        new_or_label = QLabel(self)
        new_or_label.setGeometry(self.orLabel.x(),newY,self.orLabel.width(),self.orLabel.height())

        new_or_label.setFont(self.orLabel.font())
        new_or_label.setStyleSheet(self.orLabel.styleSheet())
        new_or_label.setText(self.orLabel.text())

        new_or_label.setAlignment(self.orLabel.alignment())

        self.original_widget_values[new_or_label] = {
            'geometry': new_or_label.geometry(),
            'font_size': new_or_label.font().pointSize() if isinstance(new_or_label, (QLineEdit, QComboBox)) else None
        }

        return new_or_label
    
    def newBooleanSearchType(self):
        newY = self.booleanSearchType.y() + (self.booleanSearchType.height() + self.textOffsetY) * self.duplicateCount

        # Duplicating the QComboBox when the text editor is duplicated.
        new_boolean_box = QComboBox(self)
        new_boolean_box.setGeometry(self.booleanSearchType.x() - self.textOffsetX,newY,self.booleanSearchType.width(),self.booleanSearchType.height())

        new_boolean_box.setFont(self.booleanSearchType.font())
        new_boolean_box.setStyleSheet(self.booleanSearchType.styleSheet())

        for i in range(self.booleanSearchType.count()):
            new_boolean_box.addItem(self.booleanSearchType.itemText(i))

        self.original_widget_values[new_boolean_box] = {
            'geometry': new_boolean_box.geometry(),
            'font_size': new_boolean_box.font().pointSize() if isinstance(new_boolean_box, (QLineEdit, QComboBox)) else None
        }

        return new_boolean_box

    # This method helps in removing the extra search boxes.
    def removeTextEdit(self):
        if self.duplicateTextEdits:  # Check if there are any duplicates to remove
            last_text_edit = self.duplicateTextEdits.pop()  # Remove the last QLineEdit from the list
            last_text_edit.deleteLater()  # Delete the QLineEdit widget

            last_boolean_box = self.duplicateCombos.pop()
            last_boolean_box.deleteLater()

            last_boolean_type = self.duplicateSearchTypes.pop()
            last_boolean_type.deleteLater()
            self.duplicateCount -= 1  # Decrement the count of duplicates

            newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 1)
            self.addFieldButton.setGeometry(self.addFieldButton.x(), newY, self.addFieldButton.width(), self.addFieldButton.height())
            self.removeFieldButton.setGeometry(self.removeFieldButton.x(), newY, self.removeFieldButton.width(), self.removeFieldButton.height())

            newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 2)
            self.search.setGeometry(self.search.x(), newY, self.search.width(), self.search.height())

            newY = self.textEdit.y() + (self.textEdit.height() + self.textOffsetY) * (self.duplicateCount + 3)
            self.clearButton.setGeometry(self.clearButton.x(), newY, self.clearButton.width(), self.clearButton.height())

        else:
            QMessageBox.information(self, "Minimum Fields Reached" if self.language_value == "English" else "Cases minimum atteints", "There are no more search fields to remove." if self.language_value == "English" else "Il n'y a plus de cases de recherche à supprimer.")

    def clearSearch(self):
        for i in range(len(self.duplicateTextEdits)):
            self.removeTextEdit()
        self.textEdit.clear()
        self.booleanSearchType.setCurrentIndex(0)

    def settingsDisplay(self):
        settings = settingsPage.get_instance(self.widget)
        self.widget.addWidget(settings)
        self.widget.setCurrentIndex(self.widget.currentIndex() + 1)

    def searchToDisplay(self,results):
        from src.user_interface.searchDisplay import searchDisplay
        search = searchDisplay.replace_instance(self.widget, results)
        self.widget.addWidget(search)
        self.widget.setCurrentIndex(self.widget.currentIndex() + 1)
        # search.display_results_in_table(results) 

    # This method is responsible sending the text in the back end for the searching the value
    def search_button_clicked(self):
        institution = settings_manager.get_setting('institution')

        # Do not search if no institution selected to search.
        if institution == "":
            QMessageBox.information(self, "No institution selected" if self.language_value == "English" else "Aucun établissement sélectionné", "You have no institution selected. Please select an institution on the settings page." if self.language_value == "English" else "Vous n'avez sélectionné aucun institut. Veuillez sélectionner un institut sur la page des paramètres.")
            return

        searchText = self.textEdit.text().strip()
        if searchText != "":
            terms = [searchText]
        else:
            terms = []
        searchTypeIndex = self.booleanSearchType.currentIndex()
        searchType = "Title" if searchTypeIndex == 0 else "Platform_eISBN" if searchTypeIndex == 1 else "OCN"
        searchTypes = [searchType]
        query = f"SELECT [{institution}], File_Name, Platform, Title, Publisher, Platform_YOP, Platform_eISBN, OCN, agreement_code, collection_name, title_metadata_last_modified FROM table_name WHERE "

        if self.sender() == self.textEdit:
            # Trigger the click event of the search button only if the sender is the textEdit
            self.pushButton.click()
        # grabs the terms and searchTypes of each textbox for the search query:
        for i in range(len(self.duplicateTextEdits)):
            searchText = self.duplicateTextEdits[i].text().strip()
            if searchText != "":
                terms.append(searchText)
            searchTypeIndex = self.duplicateSearchTypes[i].currentIndex()
            searchType = "Title" if searchTypeIndex == 0 else "Platform_eISBN" if searchTypeIndex == 1 else "OCN"
            searchTypes.append(searchType)

        if len(terms) == 0:
            QMessageBox.information(self, "No Search Items" if self.language_value == "English" else "Aucun Terme de Recherche", "There are no search items in the search boxes." if self.language_value == "English" else "Il n'y a aucun terme de recherche dans les cases de recherche.")
            return

        connection = connect_to_database()
        results = search_database(connection, query, terms, searchTypes)
        close_database(connection)

        # Do not go to results page if there are no results or no text in the search field.
        if len(results) == 0:
            QMessageBox.information(self, "No Results Found" if self.language_value == "English" else "Aucun résultat trouvé", "There are no results for the search." if self.language_value == "English" else "Il n'y a aucun résultat pour la recherche.")
            return

        self.searchToDisplay(results)
        

    
    """
    This was made my chatGPT yo, do not sue me. 
    - Ethan
    Feb 27, 2024 

    You may notice this differs from the update_all_sizes method on other pages. Search boxes required extra functionality. 
    There is issues with I think empty widgets being stored, but I just threw in a try/except that seems to bandaid it. 
    - Ethan
    Mar 4th
    """
    def update_all_sizes(self):
        self.new_width = self.width() + 25
        self.new_height = self.height()

        self.textOffsetX = int(self.originalOffsetX  * (self.new_width / self.original_width))
        self.textOffsetY = int(10 * (self.new_height / self.original_height))

        if self.original_widget_values is None:
            # If it's the first run, store the original values
            self.original_widget_values = {}
            for widget in self.findChildren(QWidget):
                self.original_widget_values[widget] = {
                    'geometry': widget.geometry(),
                    'font_size': widget.font().pointSize() if isinstance(widget, (QLineEdit, QComboBox)) else None
                }

        # Iterate through every widget loaded using loadUi
        for widget, original_values in self.original_widget_values.items():
            # Calculate new geometry and size for each widget
            x = int(original_values['geometry'].x() * (self.new_width / self.original_width))
            y = int(original_values['geometry'].y() * (self.new_height / self.original_height))
            width = int(original_values['geometry'].width() * (self.new_width / self.original_width))
            height = int(original_values['geometry'].height() * (self.new_height / self.original_height))

            try:
                # If the widget is a QLineEdit or QComboBox, adjust font size
                if isinstance(widget, (QLineEdit, QComboBox)):
                    font = widget.font()
                    original_font_size = original_values['font_size']
                    if original_font_size is not None:
                        font.setPointSize(int(original_font_size * (self.new_width / self.original_width)))
                    widget.setFont(font)
                # Set the new geometry and size
                widget.setGeometry(x, y, width, height)
                
            except RuntimeError:
                continue
                # print("Widget resizing error") # All these damn prints getting annoying - E
        self.adjustDuplicateTextEditSize()

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

