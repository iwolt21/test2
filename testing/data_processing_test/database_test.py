import unittest
from unittest.mock import MagicMock, patch, call
import sqlite3
from src.data_processing import database


class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor

    @patch('src.utility.settings_manager.Settings.get_setting')
    def test_connect_to_database(self, mock_get_setting):
        mock_get_setting.return_value = 'test_database.db'
        with patch('src.data_processing.database.sqlite3.connect') as mock_connect:
            mock_connect.return_value = self.mock_connection
            connection = database.connect_to_database()
            self.assertEqual(connection, self.mock_connection)
            mock_connect.assert_called_once_with('test_database.db')

    def test_close_database(self):
        database.close_database(self.mock_connection)
        self.mock_connection.commit.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.utility.settings_manager.Settings.get_setting')
    def test_get_CRKN_tables_allow_true(self, mock_get_setting):
        mock_get_setting.return_value = "True"
        self.mock_connection.execute.return_value.fetchall.return_value = [('table1',), ('table2',)]
        tables = database.get_CRKN_tables(self.mock_connection)
        self.assertEqual(tables, ['table1', 'table2'])
        mock_get_setting.assert_called_once_with('allow_CRKN')

    @patch('src.utility.settings_manager.Settings.get_setting')
    def test_get_CRKN_tables_allow_true(self, mock_get_setting):
        mock_get_setting.return_value = "False"
        tables = database.get_CRKN_tables(self.mock_connection)
        self.assertEqual(tables, [])
        mock_get_setting.assert_called_once_with('allow_CRKN')

    def test_get_local_tables(self):
        self.mock_connection.execute.return_value.fetchall.return_value = [('local1',), ('local2',)]
        tables = database.get_local_tables(self.mock_connection)
        self.assertEqual(tables, ['local_local1', 'local_local2'])

    def test_get_tables_integration(self):
        with patch('src.data_processing.database.get_CRKN_tables') as mock_get_CRKN_tables, \
                patch('src.data_processing.database.get_local_tables') as mock_get_local_tables:
            mock_get_CRKN_tables.return_value = ['crkn_table']
            mock_get_local_tables.return_value = ['local_table']
            tables = database.get_tables(self.mock_connection)
            self.assertIn('crkn_table', tables)
            self.assertIn('local_table', tables)

    @patch('src.data_processing.database.sqlite3.connect')
    def test_tables_need_creation(self, mock_connect):
        """Test the scenario where both tables need to be created."""

        mock_connect.return_value = self.mock_connection

        self.mock_cursor.execute().fetchall.side_effect = [[], [], [], []]
        database.create_file_name_tables(self.mock_connection)

        # Verify that the table creation SQL commands were executed
        calls = [
            patch('database.sqlite3.connect'),
            unittest.mock.call("""SELECT name FROM sqlite_master WHERE type='table' AND name='CRKN_file_names'; """),
            unittest.mock.call().fetchall(),
            unittest.mock.call("CREATE TABLE CRKN_file_names(file_name VARCHAR(255), file_date VARCHAR(255));"),
            unittest.mock.call("""SELECT name FROM sqlite_master WHERE type='table' AND name='local_file_names'; """),
            unittest.mock.call().fetchall(),
            unittest.mock.call("CREATE TABLE local_file_names(file_name VARCHAR(255), file_date VARCHAR(255));")
        ]
        self.mock_cursor.execute.assert_has_calls(calls[1:], any_order=True)

    @patch('src.data_processing.database.sqlite3.connect')
    def test_tables_already_exist(self, mock_connect):
        """Test the scenario where both tables already exist."""
        mock_connect.return_value = self.mock_connection

        # Simulate the tables already existing by returning a non-empty list
        self.mock_cursor.execute().fetchall.side_effect = [[('CRKN_file_names',)], [('local_file_names',)]]

        database.create_file_name_tables(self.mock_connection)

        # Define the expected calls to check for table existence
        expected_calls = [
            unittest.mock.call("""SELECT name FROM sqlite_master WHERE type='table' AND name='CRKN_file_names'; """),
            unittest.mock.call().fetchall(),
            unittest.mock.call("""SELECT name FROM sqlite_master WHERE type='table' AND name='local_file_names'; """),
            unittest.mock.call().fetchall(),
        ]

        # Verify that only the table existence checks were performed
        self.mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)

        # Ensure that table creation statements were not executed
        creation_calls = [
            unittest.mock.call("CREATE TABLE CRKN_file_names(file_name VARCHAR(255), file_date VARCHAR(255));"),
            unittest.mock.call("CREATE TABLE local_file_names(file_name VARCHAR(255), file_date VARCHAR(255));")
        ]

        for call in creation_calls:
            self.assertNotIn(call, self.mock_cursor.execute.mock_calls,
                             "Table creation SQL should not have been executed.")

    @patch('src.data_processing.database.get_tables')
    @patch('src.utility.settings_manager.Settings.get_setting')
    def test_search_by_title_with_wildcards(self, mock_get_setting, mock_get_tables):
        # Setup mock response for database queries
        mock_get_tables.return_value = ['crkn_table1', 'crkn_table2', 'local_table1', 'local_table2']
        mock_get_setting.return_value = "TestInstitution"

        institution_columns = [('column1',), ('column2',), ('institution',), ('column4',), ('column5',), ('column6',),
                               ('column7',), ('column8',), ('TestInstitution',)]
        self.mock_cursor.description = institution_columns

        # Mock the return value for cursor.fetchall to simulate matching rows in each table
        self.mock_cursor.fetchall.side_effect = [
            [],  # First call for 'select * from [table]' to get institutions
            [('CRKN_EbookPARightsTracking_TaylorFrancis_2024_02_06_2.xlsx', 'Taylor & Francis Platform',
              "'Bread and Circuses' : Euergetism and municipal patronage in Roman Italy", 'Taylor & Francis', '2024',
              '9780203994948', '50028694', 'AG123', 'CollectionName', '2024-02-06')]  # Actual search results
        ]

        query = "SELECT * FROM table_name WHERE Title LIKE ?"
        terms = ["*%Bread and Circuses%"]
        searchTypes = ["Title"]
        results = database.search_database(self.mock_connection, query, terms, searchTypes)
        self.assertEqual(len(results), 1)
        self.assertIn('Bread and Circuses', results[0][2])
        formatted_query = query.replace("table_name", f"[crkn_table1]")
        self.mock_cursor.execute.assert_any_call(formatted_query, terms)

    def test_get_table_data(self):
        self.mock_cursor.fetchall.return_value = [('data1', 'data2')]
        data = database.get_table_data(self.mock_connection, 'test_table')
        self.assertEqual(data, [('data1', 'data2')])

    def test_get_table_data_with_error(self):
        self.mock_cursor.execute.side_effect = sqlite3.Error("Test Error")
        with self.assertLogs(level='ERROR') as log:
            data = database.get_table_data(self.mock_connection, 'bad_table')
            self.assertEqual(data, [])
            self.assertIn('An error occurred while fetching data from the table: Test Error', log.output[0])
