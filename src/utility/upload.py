from PyQt6.QtWidgets import QFileDialog, QApplication, QMessageBox, QDialog, QVBoxLayout, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from src.data_processing import database, Scraping
import sys
import datetime
from src.utility.logger import m_logger
from src.utility.settings_manager import Settings


settings_manager = Settings()
language = settings_manager.get_setting("language")


def upload_and_process_file():
    global language 
    """
    Upload and process local files into local database
    """
    language = settings_manager.get_setting("language")
    app = QApplication.instance()  # Try to get the existing application instance
    if app is None:  # If no instance exists, create a new one
        app = QApplication(sys.argv)

    options = QFileDialog.Option.ReadOnly

    file_paths, _ = QFileDialog.getOpenFileNames(None, "Open File" if language == "English" else "Ouvrir le fichier", "", 
                                                "CSV TSV or Excel (*.csv *.tsv *.xlsx);;All Files (*)" if language == "English" else
                                                "CSV TSV ou Excel (*.csv *.tsv *.xlsx);;Tous les fichiers (*)", options=options)

    # Iterate through selected file(s) to process them
    if file_paths:
        uploadUI = UploadUI(file_paths)
        uploadUI.exec()


class UploadUI(QDialog):
    def __init__(self, file_paths):
        super().__init__()
        self.setWindowTitle("Processing File..." if language == "English" else "Fichier en cours de traitement...")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
                
        layout = QVBoxLayout(self)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.loading_thread = UploadThread(file_paths)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loading_thread.start)

        self.loading_thread.progress_update.connect(self.update_progress)
        self.loading_thread.error_signal.connect(self.handle_error)
        self.loading_thread.get_answer_yes_no.connect(self.get_answer_yes_no)
        self.loading_thread.get_okay.connect(self.get_okay)

        self.timer.start(1000)

        self.finished = False

    def handle_error(self, title, error_msg):
        m_logger.error(error_msg)
        QMessageBox.critical(None, title, error_msg, QMessageBox.StandardButton.Ok)
        self.loading_thread.receive_response(True)

    def update_progress(self, value):
        m_logger.info(f"File upload progress at {value}%")
        self.progress_bar.setValue(value)
        if value == 100 and not self.finished:
            self.finished = True
            self.loading_thread = None
            self.close()

    def get_answer_yes_no(self, title, body):
        m_logger.info(body)
        reply = QMessageBox.question(None, title, body, 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.loading_thread.receive_response(reply == QMessageBox.StandardButton.Yes)

    def get_okay(self, title, body):
        m_logger.info(body)
        QMessageBox.information(None, title, body, QMessageBox.StandardButton.Ok)
        self.loading_thread.receive_response(True)


class UploadThread(QThread):
    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.file_length = len(file_paths)
        self.currentValue = 0
        self.one_file_progress_value = (1 / self.file_length) * 100

    progress_update = pyqtSignal(int)
    error_signal = pyqtSignal(str, str) 
    get_answer_yes_no = pyqtSignal(str, str) 
    get_okay = pyqtSignal(str, str)

    def run(self):
        self.process_files()

    def process_files(self):
        for i in range(self.file_length):
            self.currentValue = i * self.one_file_progress_value
            self.progress_update.emit(int(self.currentValue))
            self.process_file(self.file_paths[i])
        self.progress_update.emit(100)

    def process_file(self, file_path):
        """
        Process file and store in local database - similar to Scraping.download_files, but for local files
        :param file_path: string containing the path to the file 
        """
        app = QApplication.instance()  # Try to get the existing application instance
        if app is None:  # If no instance exists, create a new one
            app = QApplication(sys.argv)

        connection = database.connect_to_database()

        # Get file_name and date for table information
        file_name_with_ext = file_path.split("/")[-1]
        file_name = file_name_with_ext.split(".")
        date = datetime.datetime.now()
        date = date.strftime("%Y_%m_%d")

        # Check if local file is already in database
        result = Scraping.compare_file([file_name[0], date], "local", connection)

        self.currentValue += self.one_file_progress_value / 7
        self.progress_update.emit(int(self.currentValue))

        # If result is update, check if they want to update it
        if result == "UPDATE":
            self.get_answer_yes_no.emit("Replace File" if language == "English" else "Remplacer le fichier",
                                        f"{file_name_with_ext}\nA file with the same name is already in the local database. Would you like to replace it with the new file?" 
                                        if language == "English" else f"{file_name_with_ext}\nUn fichier du même nom se trouve déjà dans la base de données locale. Souhaitez-vous le remplacer par le nouveau fichier ?")
            reply = self.wait_for_response()
            if reply == False:
                print(language, language == "English")
                self.error_signal.emit("File Upload Cancelled" if language == "English" else "Chargement de fichier annulé",
                                        f"{file_name_with_ext}\n{'This file will not be uploaded' if language == 'English' else 'Ce fichier ne sera pas chargé'}")
                self.wait_for_response()
                database.close_database(connection)
                return
        
        self.currentValue += self.one_file_progress_value / 7
        self.progress_update.emit(int(self.currentValue))

        try:
            # Get our dataframe, check if it's good
            file_df = file_to_df(".".join(file_name), file_path)
            if file_df is None:
                self.error_signal.emit("Invalid File Type" if language == "English" else "Type de fichier invalide", 
                                        f"{file_name_with_ext}\nSelect only valid xlsx, csv or tsv files." if language == "English" else f"{file_name_with_ext}\nSélectionnez uniquement les fichiers xlsx, csv ou tsv valides.")
                self.wait_for_response()
                database.close_database(connection)
                return

            # Check if in correct format
            valid_file = Scraping.check_file_format(file_df)
            if valid_file is not True:
                self.error_signal.emit("Invalid File Format" if language == "English" else "Format de fichier invalide", 
                                       f"{file_name_with_ext}\n{valid_file}\nUpload aborted." if language == "English" else 
                                    f"{file_name_with_ext}\n{valid_file}\nChargement interrompu.")
                self.wait_for_response()
                database.close_database(connection)
                return
            
            self.currentValue += self.one_file_progress_value / 7
            self.progress_update.emit(int(self.currentValue))
            
            # If there are new institutions, check if the user wants to add them.
            # If no, cancel upload of file
            new_institutions = get_new_institutions(file_df)
            if len(new_institutions) > 0: # Get a display string of 5 institutions
                new_institutions_display = '\n'.join(new_institutions[:5]) 
                if len(new_institutions) > 5:
                    new_institutions_display += '...'
                self.get_answer_yes_no.emit("New Institutions", f"{len(new_institutions)} institution name{'s' if len(new_institutions) > 1 else ''} found that " +
                                            f"{'are' if len(new_institutions) > 1 else 'is'} not a CRKN institution and {'are' if len(new_institutions) > 1 else 'is'} not on the list of local institutions.\n\n" +
                                            f"{new_institutions_display}\n" +
                                            "Would you like to add them to the local list? \n'No' - The file will not be uploaded. \n'Yes' - The file will be uploaded, and the new institution names will be added as options" +
                                            " and will be available in the settings menu.")
                reply = self.wait_for_response()
                if reply == False:
                    self.error_signal.emit("File Upload Cancelled" if language == "English" else "Chargement de fichier annulé",
                                        f"{file_name_with_ext}\n{'This file will not be uploaded' if language == 'English' else 'Ce fichier ne sera pas chargé'}")
                    self.wait_for_response()
                    database.close_database(connection)
                    return
            
            self.currentValue += self.one_file_progress_value / 7
            self.progress_update.emit(int(self.currentValue))
            
            # Add new institutions
            for institution in new_institutions:
                settings_manager.add_local_institution(institution)
            self.currentValue += self.one_file_progress_value / 7
            self.progress_update.emit(int(self.currentValue))

            Scraping.upload_to_database(file_df, "local_" + file_name[0], connection)
            self.currentValue += self.one_file_progress_value / 7
            self.progress_update.emit(int(self.currentValue))

            Scraping.update_tables([file_name[0], date], "local", connection, result)
            self.currentValue += self.one_file_progress_value / 7
            self.progress_update.emit(int(self.currentValue) - 1)
            self.get_okay.emit("File Upload" if language == "English" else "Chargement de fichiers", f"{file_name_with_ext}\nYour file has been uploaded. {len(file_df)} rows have been added." if language == "English" else f"{file_name_with_ext}\nVotre fichier a été chargé. {len(file_df)} lignes ont été ajoutées.")
            self.wait_for_response()

        except Exception as e:
            self.error_signal.emit("Error" if language == "English" else "Erreur", f"{file_name_with_ext}\nAn error occurred during file processing: {str(e)}" if language == "English" else f"{file_name_with_ext}\nUne erreur s'est produite lors du traitement du fichier: {str(e)}")

        database.close_database(connection)

    def wait_for_response(self):
        # This function halts the execution of the thread until response is received
        self.response = None
        while self.response is None:
            self.msleep(100)  # Sleep to avoid busy waiting
        return self.response
    
    def receive_response(self, response):
        self.response = response


def get_new_institutions(file_df):
    """
    Get and return list of institutions that are not in either the CRKN or local list from a new file dataframe
    :param file_df: file in the form of a pandas dataframe
    :return: list of new string institutions
    """

    # If no dataframe, there's no new institutions
    if file_df is None:
        return []
    headers = file_df.columns.to_list()
    new_inst = []

    # For institution in institution section of dataframe
    for inst in headers[8:-2]:
        if inst not in settings_manager.get_setting("CRKN_institutions"):
            if inst not in settings_manager.get_setting("local_institutions"):
                if inst.strip():
                    # If not in either list and isn't blank, add to new list
                    new_inst.append(inst)
    return new_inst


def file_to_df(file_name, file_path):
    """
    Convert a file to a dataframe
    :param file_name: A string of format name.ext
    :param file_path: A string containing the file path.
    :return: Dataframe or None
    """
    m_logger.info(f"Processing file: {file_path}")
    file_extension = file_name.split(".")[-1]
    # Convert file into dataframe
    if file_extension == "csv":
        file_df = Scraping.file_to_dataframe_csv(file_name, file_path)
    elif file_extension == "xlsx":
        file_df = Scraping.file_to_dataframe_excel(file_name, file_path)
    elif file_extension == "tsv":
        file_df = Scraping.file_to_dataframe_tsv(file_name, file_path)
    else:
        return None
    return file_df


def remove_local_file(file_name):
    """
    Remove local file from database - helper function for Scraping.update_tables
    :param file_name: the name of the file to remove
    """
    connection = database.connect_to_database()
    Scraping.update_tables([file_name], "local", connection, "DELETE")
    database.close_database(connection)