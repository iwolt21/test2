from PyQt6.QtWidgets import QFileDialog, QApplication, QMessageBox
import pandas as pd
import sys
from src.utility.logger import m_logger
from src.utility.settings_manager import Settings


settings_manager = Settings()


def export_data(data, headers):
    """
    Export the data in the form of a tsv file
    :param data: data to export - in the form of a list
    :param headers: headers of the columns - in the form of a list
    """
    language = settings_manager.get_setting("language")
    app = QApplication.instance()  # Try to get the existing application instance
    if app is None:  # If no instance exists, create a new one
        app = QApplication(sys.argv)

    df = pd.DataFrame(data, columns=headers)

    # Get the file path to save the TSV file
    save_path = get_save_path()

    if save_path:
        # Append ".tsv" if the file doesn't have an extension
        if not save_path.lower().endswith('.tsv'):
            save_path += '.tsv'

        # Save the DataFrame to TSV
        df.to_csv(save_path, sep="\t", index=False)
        m_logger.info(f"Data exported to: {save_path}")
        QMessageBox.information(None, "File Export" if language == "English" else "Exportation de fichiers", f"File has been exported to:\n{save_path}" if language == "English" else f"Le fichier a été exporté vers:\n{save_path}", QMessageBox.StandardButton.Ok)


def get_save_path():
    """
    Get the save path of the file to export. This is a path selected by the user in their file structure.
    :return: The save path.
    """
    language = settings_manager.get_setting("language")
    options = QFileDialog.Option.ReadOnly
    save_path, _ = QFileDialog.getSaveFileName(None, "Save Data" if language == "English" else "Enregistrer le fichier", "", "TSV Files (*.tsv);;All Files (*)" if language == "English" else "Fichiers TSV (*.tsv);;Tous les fichiers (*)", options=options)

    return save_path
