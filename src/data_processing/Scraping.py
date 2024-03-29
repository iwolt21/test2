"""
This file includes functions for scraping from the CRKN website and uploading the new data to the database
Some functions can also be re-used for the local file uploads (compare_file)

I tested new files and the same files, but not when the file has a newer date (to update)
"""
import requests.exceptions
import time
from bs4 import BeautifulSoup
import requests
import pandas as pd
from src.utility.settings_manager import Settings
from src.data_processing import database
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from src.utility.logger import m_logger
import os

settings_manager = Settings()

"""
Ethan Penney
March 18, 2024
Created a class variant of scraping functions that are threaded and emit signals in tandem with scraping_ui.py to update loading bar. 
"""


class ScrapingThread(QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        self.scrapeCRKN()

    progress_update = pyqtSignal(int)
    file_changes_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def retry_scrape(self, attempt, max_attempt=3):
        """ Attempt to scrape again if connection is lost in the middle of scraping"""
        if attempt >= max_attempt:
            return False
        # wait for 1 second before retrying
        time.sleep(1)
        return True

    def scrapeCRKN(self):
        crkn_url = settings_manager.get_setting('CRKN_url')
        self.progress_update.emit(0)
        """Scrape the CRKN website for listed ebook files."""
        error = ""
        error_message = ""
        attempt = 0

        # Show the user scraping has started
        self.progress_update.emit(5)

        while attempt < 3:
            try:
                # Make a request to the CRKN website
                response = requests.get(crkn_url)
                # Check if request was successful (status 200)
                response.raise_for_status()
                # If request successful, process text
                page_text = response.text
                # Exit loop on successful scrape
                break

            except requests.exceptions.HTTPError as http_err:
                # Handle HTTP errors
                if settings_manager.get_setting("language") == "English":

                    error_message = ("Server Connection Error: Please make sure you are connected "
                                     "to your internet and the CRKN URL is updated in the Settings page.")

                else:
                    error_message = ("Erreur de connexion au serveur : Veuillez vous assurer que vous êtes connecté à "
                                     "votre internet et que l'URL de CRKN est mise à jour dans la page des paramètres.")
                error = http_err
                page_text = None
                if not self.retry_scrape(attempt):
                    return
            except requests.exceptions.ConnectionError as conn_err:
                # Handle errors like refused connections
                if settings_manager.get_setting("language") == "English":
                    error_message = ("Internet Connection Error : Please make sure you are connected "
                                     "to your internet.")
                else:
                    error_message = ("Erreur de Connexion Internet : Veuillez vous assurer que "
                                     "vous êtes connecté à votre internet.")
                error = conn_err
                page_text = None
                if not self.retry_scrape(attempt):
                    return
            except requests.exceptions.Timeout as timeout_err:
                # Handle request timeout
                if settings_manager.get_setting("language") == "English":
                    error_message = "Connection Timeout: Please try again later."
                else:
                    error_message = "Délai de connexion dépassé : Veuillez essayer de mettre à jour CRKN à nouveau."
                error = timeout_err
                page_text = None
            except Exception as e:
                # Handle any other exceptions
                if settings_manager.get_setting("language") == "English":
                    error_message = ("Unexpected Error : Please make sure you are connected "
                                     "to the internet.")
                else:
                    error_message = "Erreur inattendue : Veuillez réessayer plus tard."
                error = e
                page_text = None
            attempt += 1

        # Log and display error message
        if page_text is None:
            m_logger.error(f"An error occurred: {error}")
            self.error_signal.emit(error_message)
            return

        # Get list of links that end in xlsx, csv, or tsv from the CRKN website link
        soup = BeautifulSoup(page_text, "html.parser")
        links = soup.find_all('a', href=lambda href: href and (href.endswith('.xlsx') or href.endswith('.csv') or href.endswith('.tsv')))

        connection = database.connect_to_database()

        # List of files that need to be updated/added to the local database
        files_to_update = []
        # All CRKN tables - by end it will just have the ones to remove
        files_to_remove = [file for file in database.get_tables(connection) if not file.startswith("local_")]

        # Check if links on CRKN website need to be added/updated in local database
        i = 0
        for link in links:
            i += 1
            progress = 10 + int((i / len(links)) * 20)
            self.progress_update.emit(progress)
            file_link = link.get("href")
            file_first, file_date = split_CRKN_file_name(file_link)
            result = compare_file([file_first, file_date], "CRKN", connection)

            # If result (update or insert into), add to update list
            if result:
                files_to_update.append([link, result])

            try:
                files_to_remove.remove(file_first)
            except ValueError:
                pass

        # Ask user if they want to perform scraping (slightly time-consuming)
        file_changes = len(files_to_update) + len(files_to_remove)
        if file_changes > 0:
            self.file_changes_signal.emit(file_changes)
            ans = self.wait_for_response()
            if ans == "Y":
                if len(files_to_update) > 0:
                    self.download_files(files_to_update, connection)
                if len(files_to_remove) > 0:
                    i = 0
                    for file in files_to_remove:
                        i += 1
                        progress = 90 + int((i / len(files_to_remove)) * 9)
                        self.progress_update.emit(progress)
                        update_tables([file], "CRKN", connection, "DELETE")

        # Scrape CRKN institution list from a CRKN file in the database
        crkn_tables = connection.execute("SELECT file_name FROM CRKN_file_names;").fetchall()
        # strip the apostrophes/parentheses from formatting
        crkn_tables = [row[0] for row in crkn_tables]

        if len(crkn_tables) > 0:
            institutions = connection.cursor().execute(f'select * from [{crkn_tables[0]}]')
            institutions = [description[0] for description in institutions.description[8:-2]]
        else:
            institutions = []
        settings_manager.set_CRKN_institutions(institutions)

        database.close_database(connection)
        self.progress_update.emit(100)

    def wait_for_response(self):
        # This function halts the execution of the thread until response is received
        self.response = None
        while self.response is None:
            self.msleep(100)  # Sleep to avoid busy waiting
        return self.response

    def receive_response(self, response):
        self.response = response
    
    def download_files(self, files, connection):        
        """
        For all files that need downloading from CRKN, do so and store in local database.
        :param files: list of files to download from CRKN
        :param connection: database connection object
        """
        language = settings_manager.get_setting("language")
        try:
            i = 0
            for [link, command] in files:
                i += 1
                progress = 30 + int((i / len(files)) * 30)
                self.progress_update.emit(progress)
                file_link = link.get("href")

                # Get which type of file it is (xlsx, csv, or tsv)
                file_type = file_link.split(".")[-1]

                # Platform, date/version number
                file_first, file_date = split_CRKN_file_name(file_link)

                # Write file to temporary local file
                with open(f"{os.path.abspath(os.path.dirname(__file__))}/temp.{file_type}", 'wb') as file:
                    response = requests.get(settings_manager.get_setting("CRKN_root_url") + file_link)
                    file.write(response.content)

                # Convert file into dataframe
                if file_type == "xlsx":
                    file_df = file_to_dataframe_excel(file_link.split("/")[-1], f"{os.path.abspath(os.path.dirname(__file__))}/temp.xlsx")
                elif file_type == "tsv":
                    file_df = file_to_dataframe_tsv(file_link.split("/")[-1], f"{os.path.abspath(os.path.dirname(__file__))}/temp.tsv")
                else:
                    file_df = file_to_dataframe_csv(file_link.split("/")[-1], f"{os.path.abspath(os.path.dirname(__file__))}/temp.csv")

                # Check if in correct format, if it is, upload and update tables
                valid_format = check_file_format(file_df)
                if valid_format is True:
                    upload_to_database(file_df, file_first, connection)
                    update_tables([file_first, file_date], "CRKN", connection, command)
                else:
                    m_logger.error(f"{file_link.split('/')[-1]} - The file was not in the correct format, so it was not uploaded.\n{valid_format}")
                    self.error_signal.emit(f"{file_link.split('/')[-1]}\nThe file was not in the correct format, so it was not uploaded.\n{valid_format}")

        # Handle connection loss in middle of scraping
        except requests.exceptions.HTTPError as http_err:
            # Handle HTTP errors
            if language == "English":
                error_message = ("Internet Connection Error : Connection to the server was lost. Not all files have been successfully retreived. Please try updating CRKN again.")
            else:
                error_message = ("Erreur de Connexion Internet : La connexion su serveur a été perdue. Tous les fichiers n'ont pas été récupérés. Veuillez réessayer de mettre  à jour RCDR de nouveau.")
            m_logger.error(http_err)
            self.error_signal.emit(error_message)
        except requests.exceptions.ConnectionError as conn_err:
            # Handle errors like refused connections
            if language == "English":
                error_message = ("Internet Connection Error : Connection to the internet was lost. Not all files have been successfully retreived. Please try updating CRKN again.")
            else:
                error_message = (
                    "Erreur de Connexion Internet : La connexion à l'internet a été perdue. Tous les fichiers n'ont pas été récupérés avec succès. Veuillez réessayer de mettre à jour RCDR de nouveau.")
            m_logger.error(conn_err)
            self.error_signal.emit(error_message)
        except requests.exceptions.Timeout as timeout_err:
            # Handle request timeout
            if language == "English":
                error_message = "Connection Timeout : The server took too long to respond. Not all files have been successfully retrieved. Please try updating CRKN again."
            else:
                error_message = "Expiration de la Connexion : Le serveur a mis trop de temps à répondre. Tous les fichiers n'ont pas été récupérés avec succès. Veuillez réessayer de mettre  à jour RCDR de nouveau."
            m_logger.error(timeout_err)
            self.error_signal.emit(error_message)
        except Exception as e:
            # Handle any other exceptions
            if language == "English":
                error_message = ("Unexpected Error : Not all files have been successfully retrieved. "
                                 "Please try updating CRKN again.")
            else:
                error_message = "Erreur inattendue : Tous les fichiers n'ont pas été récupérés avec succès. Veuillez réessayer de mettre  à jour RCDR de nouveau."
            m_logger.error(e)
            self.error_signal.emit(error_message)

        # Remove temp.xlsx used for uploading files
        try:
            os.remove(f"{os.path.abspath(os.path.dirname(__file__))}/temp.xlsx")
        except FileNotFoundError:
            pass
        try:
            os.remove(f"{os.path.abspath(os.path.dirname(__file__))}/temp.csv")
        except FileNotFoundError:
            pass
        try:
            os.remove(f"{os.path.abspath(os.path.dirname(__file__))}/temp.tsv")
        except FileNotFoundError:
            pass


def compare_file(file, method, connection):
    """
    Compare file to see if it is already in database.
    :param file: file name information - [publisher, date/version number]
    :param method: CRKN or local
    :param connection: database connection object
    :return: False if no update needed. Update command if update needed (INSERT INTO or UPDATE)
    """
    if method != "CRKN" and method != "local":
        raise Exception("Incorrect method type (CRKN or local) to indicate type/location of file")

    cursor = connection.cursor()

    # Get list of files (only one) that matches the file name
    files = cursor.execute(f"SELECT * FROM {method}_file_names WHERE file_name = '{file[0]}'").fetchall()

    # If list is empty, file doesn't exist, insert the file
    if not files:
        return "INSERT INTO"

    # File is in database - check if it needs to be updated - if file_date is new, or local
    else:
        files_dates = cursor.execute(
            f"SELECT * FROM {method}_file_names WHERE file_name = '{file[0]}' and file_date = '{file[1]}'").fetchall()
        if not files_dates or method == "local":
            return "UPDATE"

        # No update needed
        m_logger.info(f"File already there - {file[0]}, {file[1]}")
        return False


def update_tables(file, method, connection, command):
    """
    Update {method}_file_names table with file information in local database.
    :param file: file name information - [publisher, date/version number]
                 if DELETE command, can just pass publisher, but as a list ([publisher])
                 publisher, or name of table if it is different (local files)
    :param method: CRKN or local
    :param connection: database connection object
    :param command: INSERT INTO, UPDATE, or DELETE
    """
    if method != "CRKN" and method != "local":
        raise Exception("Incorrect method type (CRKN or local) to indicate type/location of file")

    cursor = connection.cursor()

    try:
        # Table does not exist, insert name and data/version
        if command == "INSERT INTO":
            cursor.execute(f"INSERT INTO {method}_file_names (file_name, file_date) VALUES ('{file[0]}', '{file[1]}')")
            m_logger.info(f"file name inserted - {file[0]}, {file[1]}")

        # File exists, but needs to be updated, change date/version
        elif command == "UPDATE":
            cursor.execute(f"UPDATE {method}_file_names SET file_date = '{file[1]}' WHERE file_name = '{file[0]}';")
            m_logger.info(f"file name updated - {file[0]}, {file[1]}")

        # Delete file from {method}_file_names table and drop the table as well.
        elif command == "DELETE":
            cursor.execute(f"DELETE from {method}_file_names WHERE file_name = '{file[0]}'")
            if method == "CRKN":
                cursor.execute(f"DROP TABLE {file[0]}")
            else:
                cursor.execute(f"DROP TABLE [local_{file[0]}]")
        # Commit changes on successful operation
        connection.commit()
    except Exception as e:
        # Rollback if changes fail
        connection.rollback()
        m_logger.error(f"Failed to {command} data for {file[0]}: {e}. Database remains unchanged")


def split_CRKN_file_name(file_name):
    """
    Split CRKN file name.
    :param file_name: string CRKN file name
    :return: list of two elements - publisher name and date/version number
    """
    file = file_name.split("/")[-1]
    a = file.split("_")
    c = "_".join(a[3:]).split(".")[0]

    # a[2] = Platform name, c = data/update version
    return [a[2], c]


def file_to_dataframe_excel(file_name, file):
    """
    Convert Excel file to pandas dataframe.
    File can be either a file or a URL link to a file.
    :param file_name: the file name being uploaded
    :param file: local file to convert to dataframe
    :return: dataframe, or error string
    """
    try:
        df = pd.read_excel(file, sheet_name="PA-Rights")

        # Check top left cell for platform, return if missing (catch in check_file_format)
        platform = df.columns[0]
        if platform == "Unnamed: 0":
            m_logger.error("File to Dataframe failed - No Platform listed.")
            return "No Platform"

        # Remove top two rows, set header
        df = df.set_axis(df.values[1], axis="columns")
        df = df.drop([0, 1])

        # Add platform and file_name to dataframe
        df["Platform"] = platform
        df["File_Name"] = file_name
        df = df.reset_index(drop=True)
        return df
    except ValueError:
        m_logger.error("Incorrect sheet name in excel file (PA-Rights did not exist).")
        return "PA-Rights"


def file_to_dataframe_csv(file_name, file):
    """
    Convert csv file to pandas dataframe.
    File can be either a file or a URL link to a file.
    :param file_name: the file name being uploaded
    :param file: local file to convert to dataframe
    :return: dataframe, or error string
    """
    try:
        df = pd.read_csv(file)

        # Check top left cell for platform, return if missing (catch in check_file_format)
        platform = df.columns[0]
        if platform == "Unnamed: 0":
            m_logger.error("File to Dataframe failed - No Platform listed.")
            return "No Platform"

        # Remove top two rows, set header
        df = df.set_axis(df.values[1], axis="columns")
        df = df.drop([0, 1])

        # Add platform and file_name to dataframe
        df["Platform"] = platform
        df["File_Name"] = file_name
        df = df.reset_index(drop=True)
        return df
    except Exception:
        m_logger.error("File to Dataframe failed - Unable to read csv file.")
        return "PA-Rights"


def file_to_dataframe_tsv(file_name, file):
    """
        Convert tsv file to pandas dataframe.
        File can be either a file or a URL link to a file.
        :param file_name: the file name being uploaded
        :param file: local file to convert to dataframe
        :return: dataframe, or error string
        """
    try:
        df = pd.read_table(file)

        # Check top left cell for platform, return if missing (catch in check_file_format)
        platform = df.columns[0]
        if platform == "Unnamed: 0":
            m_logger.error("File to Dataframe failed - No Platform listed.")
            return "No Platform"

        # Remove top two rows, set header
        df = df.set_axis(df.values[1], axis="columns")
        df = df.drop([0, 1])

        # Add platform and file_name to dataframe
        df["Platform"] = platform
        df["File_Name"] = file_name
        df = df.reset_index(drop=True)
        return df
    except Exception:
        m_logger.error("File to Dataframe failed - Unable to read tsv file.")
        return "PA-Rights"


def upload_to_database(df, table_name, connection):
    """
    Upload file dataframe to table in database.
    :param df: dataframe with data
    :param table_name: table to insert data into
    :param connection: database connection object
    """

    try:
        df.to_sql(
            name=table_name,
            con=connection,
            if_exists="replace",
            index=False
        )
        cursor = connection.cursor()
        # Fixes the date format in the database directly; removes the seconds
        cursor.execute(f'''UPDATE {table_name}
                    SET title_metadata_last_modified = strftime('%Y-%m-%d', title_metadata_last_modified)''')

        connection.commit()
    except Exception as e:
        # Rollback in case of error
        connection.rollback()
        m_logger.error(f"Failed to upload data to {table_name}: {e}. Database remains unchanged.")


def check_file_format(file_df):
    """
    Checks the incoming file format to see if it is correct
    :param file_df: dataframe with file info (or None if unable to turn into dataframe
    :return: True if valid, error string if not
    """

    if isinstance(file_df, pd.DataFrame):
        header_row = ["Title", "Publisher", "Platform_YOP", "Platform_eISBN", "OCN", "agreement_code",
                      "collection_name", "title_metadata_last_modified"]
        headers = file_df.columns.to_list()

        for i in range(min(len(headers), 8)):
            if headers[i] != header_row[i]:
                m_logger.error("The header row is incorrect")
                return f"Missing or incorrect header column '{header_row[i]}' in column {i+1} (A=1)."
        if len(headers) < 8:
            m_logger.error("Missing columns in the header row")
            return f"Missing columns in the header row."

        # Title, ISBN and Y/N Column complete
        df_series = file_df.count()
        rows = file_df.shape[0]
        if df_series["Title"] != rows:
            m_logger.error("Missing title data")
            return "Missing title data."
        # if df_series["Platform_eISBN"] != rows:
        #     m_logger.error("Missing ISBN data")
        #     return "Missing Platform_eISBN data."
        for institution_column in df_series[8:-2]:
            if institution_column != rows:
                m_logger.error("Missing Y/N data")
                return "Missing Y/N data"

        return True

    # Failed to read the file into dataframe - return error instead
    elif file_df == "No Platform":
        return "No platform listed in cell A1."
    elif file_df == "PA-Rights":
        return "The 'PA-Rights' sheet does not exist."
    else:
        return "Unknown error."
