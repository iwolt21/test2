"""
DATABASE STRUCTURE:

Table 1: CRKN_file_names: (file_name, file_date)
        - Contains a list of all the tables that contain CRKN file data
        - file_name = first part of file link name on CRKN website
        - file_date = date and version number of file link name on CRKN website

Table 2: local_file_names: (file_name, file_date)
        - Contains a list of all the tables that contain local file data
        - NOTE: Does not include "local_" that is at the beginning of the actual tables
        - file_name = entire file name that is uploaded (without the extension)
        - file_date = the actual date that the file was uploaded to the database

Other Tables:
        - All other tables are tables listed in the two tables above
        - For CRKN_file_names - direct references (file_name)
        - For local_file_names - "local_" + file_name
"""

import sqlite3
from src.utility.logger import m_logger
from src.utility.settings_manager import Settings

settings_manager = Settings()


def connect_to_database():
    """
    Connect to local database.
    :return: database connection object
    """
    m_logger.info(f"Opening connection to the database.")
    database_name = settings_manager.get_setting('database_name')
    return sqlite3.connect(database_name)


def close_database(connection):
    """
    Close connection to local database.
    :param connection: database connection object
    """
    m_logger.info(f"Closing connection to the database.")
    connection.commit()
    connection.close()


def get_CRKN_tables(connection):
    """
    Get list of CRKN table names if allow_CKRN is True, else empty list
    :param connection: database connection object
    :return: list of CRKN table names, or empty list
    """
    # Only get if allow_CRKN is set to true, else empty list
    allow_crkn = settings_manager.get_setting('allow_CRKN')
    if allow_crkn == "True":
        crkn_tables = connection.execute("SELECT file_name FROM CRKN_file_names;").fetchall()
        # strip the apostrophes/parentheses from formatting
        return [row[0] for row in crkn_tables]
    return []


def get_local_tables(connection):
    """
    Get list of local table names
    :param connection: database connection object
    :return: list of local table names
    """
    local_tables = connection.execute("SELECT file_name FROM local_file_names;").fetchall()
    # Need to modify the table names for the local files
    return ["local_" + row[0] for row in local_tables]


def get_tables(connection):
    """
    Gets the names of all tables via the CRKN and local file name tables. Uses two helper functions.
    :param connection: database connection object
    :return: list of all CRKN/local file name tables, depending on allow_CRKN value
    """
    return get_CRKN_tables(connection) + get_local_tables(connection)


def create_file_name_tables(connection):
    """
    Create default database tables - CRKN_file_names and local_file_names
    Table name format: just the abbreviation
    :param connection: database connection object
    """

    try:
        # cursor object to interact with database
        cursor = connection.cursor()

        list_of_tables = cursor.execute(
            """SELECT name FROM sqlite_master WHERE type='table'
            AND name='CRKN_file_names'; """).fetchall()

        # If table doesn't exist, create new table for CRKN file info
        if not list_of_tables:
            m_logger.info("CRKN_file_names table does not exist, creating new one")
            cursor.execute("CREATE TABLE CRKN_file_names(file_name VARCHAR(255), file_date VARCHAR(255));")

        # Empty list for next check
        list_of_tables.clear()
        list_of_tables = cursor.execute(
            """SELECT name FROM sqlite_master WHERE type='table'
            AND name='local_file_names'; """).fetchall()

        # If table does not exist, create new table for local file info
        if not list_of_tables:
            m_logger.info("local_file_names table does not exist, creating new one")
            cursor.execute("CREATE TABLE local_file_names(file_name VARCHAR(255), file_date VARCHAR(255));")
        # Commit changes
        connection.commit()
    except sqlite3.Error as e:
        m_logger.error(f"A database error occured: {e}")
        # Rollback changes
        connection.rollback()


def search_database(connection, query, terms, searchTypes):
    """
    Database searching functionality.
    :param connection: database connection object
    :param query: SQL query - base query without any actual search terms
    :param terms: list of terms being searched
    :param searchTypes: list of searchTypes for each corresponding term
    :return: list of all matching results throughout all tables
    """
    results = []
    cursor = connection.cursor()

    list_of_tables = get_tables(connection)

    # Constructs the final query with all terms
    for i in range(len(terms)):
        # initial query won't use OR
        if i > 0:
            query += " OR "
        if '*' in terms[i]:
            terms[i] = terms[i].replace("*", "%")
            query += f"{searchTypes[i]} LIKE ?"
        else:
            if searchTypes[i] == "Title":
                query += f"LOWER({searchTypes[i]}) = LOWER(?)"
            else:
                query += f"{searchTypes[i]} = ?"

    # Searches for matching items through each table one by one and adds any matches to the list
    for table in list_of_tables:
        # Get institutions from each table
        institutions = cursor.execute(f'select * from [{table}]')
        institutions = [description[0] for description in institutions.description[8:-2]]

        # Only search table if it has the institution
        if settings_manager.get_setting("institution") in institutions:
            formatted_query = query.replace("table_name", f"[{table}]")
            # executes the final fully-formatted query
            cursor.execute(formatted_query, terms)

            results.extend(cursor.fetchall())
    return results
def get_table_data(connection, table_name):
    """
    Retrieve information from a specific table in the database.
    :param connection: database connection object
    :param table_name: name of the table to fetch data from
    :return: list of tuples containing data from the specified table
    """
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}];")
        table_data = cursor.fetchall()
        return table_data
    except sqlite3.Error as e:
        m_logger.error(f"An error occurred while fetching data from the table: {e}")
        return []