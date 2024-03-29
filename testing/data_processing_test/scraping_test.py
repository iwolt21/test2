import pytest
from unittest.mock import patch, MagicMock
import requests
from src.data_processing.Scraping import scrapeCRKN
from src.data_processing.Scraping import split_CRKN_file_name
from src.data_processing.Scraping import compare_file


class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError

#Mock HTML content
mock_html = "<html><body><a href='CRKN_EbookPARightsTracking_Proquest_2024_01_20_02.xlsx'>CRKN_EbookPARightsTracking_Proquest_2024_01_20_02.xlsx</a><a href='CRKN_EbookPARightsTracking_Proquest_2024_01_20_02.xlsx'>CRKN_EbookPARightsTracking_Proquest_2024_01_20_02.xlsx</a></body></html>"


def test_scrapeCRKN_success():
    # Mock data for the response
    mock_response = MockResponse(mock_html, 200)
    # Patching requests.get to return the mock response
    with patch('src.data_processing.Scraping.requests.get', return_value=mock_response):
        # Patching the database connection methods
        with patch('src.data_processing.database.connect_to_database') as mock_connect, \
                patch('src.data_processing.database.close_database') as mock_close:
            # Create a mock connection object
            mock_connection = MagicMock()
            mock_connect.return_value = mock_connection

            # Call the function
            scrapeCRKN()

            # Assertions to verify behavior
            mock_connect.assert_called_once()  # Verify database connection was opened
            mock_close.assert_called_once_with(mock_connection)  # Verify database connection was closed

def test_scrapeCRKN_HTTP_failure():
    # Mock data for the response
    mock_response = MockResponse(None, 404)
    # Patching requests.get to return the mock response
    with patch('src.data_processing.Scraping.requests.get', return_value=mock_response):
        # Patching the database connection methods
        with patch('src.data_processing.database.connect_to_database') as mock_connect:
            # Create a mock connection object
            mock_connection = MagicMock()
            mock_connect.return_value = mock_connection

            # Call the function
            scrapeCRKN()

            # Assertions to verify behavior
            mock_connect.assert_not_called()  # Verify database connection was opened


def test_split_CRKN_file_name():
    # Example file name
    file_name = "CRKN_PARightsTracking_ACS_2022_03_29_03"

    # Expected result
    expected_name = "ACS"
    expected_date = "2022_03_29_03"

    # Call the function
    result = split_CRKN_file_name(file_name)

    # Assert the results are as expected
    assert result[0] == expected_name, "The name part of the file is not correctly extracted"
    assert result[1] == expected_date, "The date part of the file is not correctly extracted"


def test_scrapeCRKN_html_processing():
    # Mock HTML content

    # Mock response for requests.get
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.text = mock_html

    # Mock database connection
    mock_connection = MagicMock()

    with patch('src.data_processing.Scraping.requests.get', return_value=mock_response):
        with patch('src.data_processing.database.connect_to_database', return_value=mock_connection):
            # Call the function
            scrapeCRKN()

            # Check if database connection was used to execute queries
            assert mock_connection.cursor.called, "Database cursor was not called"

            # Check if the commit was called on the database connection
            assert mock_connection.commit.called, "Database commit was not called"

            # Check if database connection was closed
            assert mock_connection.close.called, "Database connection was not closed"


def test_compare_file_new_file():
    # Mocking the database connection and cursor
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value = mock_cursor

    # Setting up the mock to return empty result for non existent file
    mock_cursor.execute.return_value.fetchall.return_value = []

    # Call the function
    result = compare_file(["test_file", "2022_01_01"], "CRKN", mock_connection)

    # Asserts
    assert result == False, "Should return False for a new file"
    mock_cursor.execute.assert_called_with("INSERT INTO CRKN_file_names (file_name, file_date) VALUES ('test_file', '2022_01_01')")