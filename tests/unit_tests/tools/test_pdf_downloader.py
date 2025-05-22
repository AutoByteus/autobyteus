# File: tests/tools/test_pdf_downloader.py

import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, Mock # Added Mock
from autobyteus.tools.pdf_downloader import PDFDownloader
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ParameterType

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def temp_dir():
    temp_dir_path = tempfile.mkdtemp() # Renamed to avoid conflict
    yield temp_dir_path
    shutil.rmtree(temp_dir_path, ignore_errors=True)

@pytest.mark.asyncio
async def test_pdf_downloader_default_config():
    downloader = PDFDownloader()
    assert downloader.download_folder == downloader.default_download_folder

@pytest.mark.asyncio
async def test_pdf_downloader_with_custom_config(temp_dir):
    config = ToolConfig(params={'custom_download_folder': temp_dir})
    downloader = PDFDownloader(config=config)
    assert downloader.download_folder == temp_dir

@pytest.mark.asyncio
async def test_get_config_schema(): # Removed mock_agent_context
    schema = PDFDownloader.get_config_schema()
    assert len(schema) == 1
    
    param = schema.get_parameter('custom_download_folder')
    assert param is not None
    assert param.param_type == ParameterType.DIRECTORY_PATH
    assert not param.required
    assert param.default_value is None

@pytest.mark.asyncio
async def test_tool_usage_xml(): # Removed mock_agent_context
    usage = PDFDownloader.tool_usage_xml()
    
    assert 'PDFDownloader: Downloads a PDF file from a given URL.' in usage
    assert '<command name="PDFDownloader">' in usage
    assert '<arg name="url">https://example.com/file.pdf</arg>' in usage

@pytest.mark.asyncio
async def test_execute_missing_url(mock_agent_context): # Added mock_agent_context
    downloader = PDFDownloader()
    
    with pytest.raises(ValueError, match="The 'url' keyword argument must be specified."):
        await downloader.execute(mock_agent_context) # Added mock_agent_context

@pytest.mark.asyncio
async def test_execute_success_mock(temp_dir, mock_agent_context): # Added mock_agent_context
    config = ToolConfig(params={'custom_download_folder': temp_dir}) # Tool configured with temp_dir
    downloader = PDFDownloader(config=config)
    
    url = 'https://example.com/test.pdf'
    mock_pdf_data = b'%PDF-1.4 fake pdf content'
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.iter_content = MagicMock(return_value=[mock_pdf_data])
        mock_get.return_value = mock_response
        
        result = await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
        
        assert "PDF successfully downloaded and saved to" in result
        assert temp_dir in result
        
        # Verify file was created
        files = os.listdir(temp_dir)
        assert len(files) == 1
        assert files[0].endswith('.pdf')

@pytest.mark.asyncio
async def test_execute_invalid_content_type(mock_agent_context): # Added mock_agent_context
    downloader = PDFDownloader()
    url = 'https://example.com/not-a-pdf.html'
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response
        
        # Tool's _execute wraps this specific error in ValueError
        with pytest.raises(ValueError, match="The URL does not point to a PDF file"):
             await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
        # The execute method catches this ValueError and returns a string message.
        # Let's test that string message if the intent is to check the friendly output.
        # If the intent is to check the raised exception, then the above is fine.
        # The source code's _execute method catches ValueError and returns its string.
        # Let's adjust to check the returned message, as per PDFDownloader._execute
        result = await downloader.execute(mock_agent_context, url=url)
        assert "The URL does not point to a PDF file" in result


@pytest.mark.asyncio
async def test_execute_network_error(mock_agent_context): # Added mock_agent_context
    downloader = PDFDownloader()
    url = 'https://nonexistent.example.com/test.pdf'
    
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        
        result = await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
        
        assert "Error downloading PDF: Network error" in result

@pytest.mark.asyncio
async def test_execute_custom_folder_parameter(temp_dir, mock_agent_context): # Added mock_agent_context
    downloader = PDFDownloader() # Default config, folder passed via execute
    url = 'https://example.com/test.pdf'
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.iter_content = MagicMock(return_value=[b'fake pdf data'])
        mock_get.return_value = mock_response
        
        result = await downloader.execute(mock_agent_context, url=url, folder=temp_dir) # Added mock_agent_context
        
        assert temp_dir in result
        assert "PDF successfully downloaded and saved to" in result
        # Verify file was created in custom folder
        files = os.listdir(temp_dir)
        assert len(files) == 1
        assert files[0].endswith('.pdf')


def test_get_name():
    assert PDFDownloader.get_name() == "PDFDownloader"

@pytest.mark.asyncio
async def test_execute_io_error(temp_dir, mock_agent_context): # Added mock_agent_context
    config = ToolConfig(params={'custom_download_folder': temp_dir})
    downloader = PDFDownloader(config=config)
    
    url = 'https://example.com/test.pdf'
    
    with patch('requests.get') as mock_get, \
         patch('builtins.open', side_effect=IOError("Permission denied")):
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.iter_content = MagicMock(return_value=[b'fake pdf data'])
        mock_get.return_value = mock_response
        
        result = await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
        
        assert "Error saving PDF: Permission denied" in result
