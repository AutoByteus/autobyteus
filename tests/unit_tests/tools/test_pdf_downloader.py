# File: tests/unit_tests/tools/test_pdf_downloader.py

import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, Mock
import requests 

import autobyteus.tools.pdf_downloader 

from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.utils.file_utils import get_default_download_folder 

TOOL_NAME_PDF_DOWNLOADER = "PDFDownloader" 

@pytest.fixture
def mock_agent_context_pdf_dl() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_pdf_dl_func"
    return mock_context

@pytest.fixture
def pdf_downloader_tool_instance(mock_agent_context_pdf_dl: AgentContext) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_PDF_DOWNLOADER)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context_pdf_dl.agent_id)
    return tool_instance

@pytest.fixture
def temp_dir_for_functional_pdf_downloader() -> str: # type: ignore
    temp_dir_path = tempfile.mkdtemp(prefix="pdf_dl_func_test_")
    yield temp_dir_path
    shutil.rmtree(temp_dir_path, ignore_errors=True)

def test_pdf_downloader_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_PDF_DOWNLOADER)
    assert definition is not None, f"Tool '{TOOL_NAME_PDF_DOWNLOADER}' not found in registry. Ensure module is imported."
    assert definition.name == TOOL_NAME_PDF_DOWNLOADER
    assert "Downloads a PDF file" in definition.description
    assert "Validates Content-Type" in definition.description 

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 
    
    param_url = schema.get_parameter("url")
    assert isinstance(param_url, ParameterDefinition)
    assert param_url.name == "url"
    assert param_url.param_type == ParameterType.STRING
    assert param_url.required is True
    assert "Parameter 'url' for tool 'PDFDownloader'" in param_url.description 

    param_folder = schema.get_parameter("folder")
    assert isinstance(param_folder, ParameterDefinition)
    assert param_folder.name == "folder"
    assert param_folder.param_type == ParameterType.STRING # MODIFIED from DIRECTORY_PATH
    assert param_folder.required is False 
    assert "Parameter 'folder' for tool 'PDFDownloader'" in param_folder.description
    assert "This is expected to be a path." in param_folder.description # Heuristic added description

    assert definition.config_schema is None 

def test_pdf_downloader_tool_usage_xml_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_PDF_DOWNLOADER)
    assert definition is not None
    xml_output = definition.usage_xml
    assert f'<command name="{TOOL_NAME_PDF_DOWNLOADER}">' in xml_output
    assert '<arg name="url" type="string"' in xml_output 
    
    expected_folder_desc = "Parameter 'folder' for tool 'PDFDownloader'. This is expected to be a path."
    import xml.sax.saxutils
    escaped_folder_desc = xml.sax.saxutils.escape(expected_folder_desc)
    assert f'<arg name="folder" type="string" description="{escaped_folder_desc}" required="false"' in xml_output # MODIFIED type
    assert '</command>' in xml_output

def test_pdf_downloader_tool_usage_json_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_PDF_DOWNLOADER)
    assert definition is not None
    json_output = definition.usage_json_dict
    assert json_output["name"] == TOOL_NAME_PDF_DOWNLOADER
    assert "Downloads a PDF file" in json_output["description"]
    
    input_schema = json_output["inputSchema"]
    assert input_schema["type"] == "object"
    assert "url" in input_schema["properties"]
    assert "folder" in input_schema["properties"]
    assert input_schema["properties"]["url"]["type"] == "string"
    assert input_schema["properties"]["folder"]["type"] == "string" # Was directory_path, mapped to string
    assert "url" in input_schema["required"]
    assert "folder" not in input_schema["required"] 

@pytest.mark.asyncio
async def test_pdf_dl_missing_url_arg(pdf_downloader_tool_instance: BaseTool, mock_agent_context_pdf_dl: AgentContext):
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_PDF_DOWNLOADER}'"):
        await pdf_downloader_tool_instance.execute(mock_agent_context_pdf_dl) 

@pytest.mark.asyncio
async def test_pdf_dl_success_default_folder(pdf_downloader_tool_instance: BaseTool, mock_agent_context_pdf_dl: AgentContext, mocker):
    mock_temp_default_folder = tempfile.mkdtemp(prefix="mock_default_pdf_")
    mocker.patch('autobyteus.tools.pdf_downloader.get_default_download_folder', return_value=mock_temp_default_folder)
    
    url = 'https://example.com/test.pdf'
    mock_pdf_data = b'%PDF-1.4 functional pdf test'
    
    mock_response = MagicMock(spec=requests.Response)
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="test_doc.pdf"'}
    mock_response.iter_content = MagicMock(return_value=[mock_pdf_data])
    mock_response.raw = MagicMock(); mock_response.raw.closed = False
    mock_response.close = MagicMock()

    with patch('autobyteus.tools.pdf_downloader.requests.get', return_value=mock_response) as mock_get_req:
        result = await pdf_downloader_tool_instance.execute(mock_agent_context_pdf_dl, url=url) 
        
    mock_get_req.assert_called_once_with(url, stream=True, timeout=30)
    assert "PDF successfully downloaded and saved to" in result
    assert mock_temp_default_folder in result 
    
    files = os.listdir(mock_temp_default_folder)
    assert len(files) == 1
    assert files[0].endswith('_test_doc.pdf') 
    with open(os.path.join(mock_temp_default_folder, files[0]), 'rb') as f:
        assert f.read() == mock_pdf_data
    mock_response.close.assert_called()
    shutil.rmtree(mock_temp_default_folder)

@pytest.mark.asyncio
async def test_pdf_dl_success_custom_folder(pdf_downloader_tool_instance: BaseTool, temp_dir_for_functional_pdf_downloader: str, mock_agent_context_pdf_dl: AgentContext):
    url = 'https://example.com/another.pdf'
    mock_pdf_data = b'%PDF-another functional test'
    
    mock_response = MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {'Content-Type': 'application/pdf'}
    mock_response.iter_content.return_value = [mock_pdf_data]
    mock_response.raw = MagicMock(); mock_response.raw.closed = False
    mock_response.close = MagicMock()

    with patch('autobyteus.tools.pdf_downloader.requests.get', return_value=mock_response):
        result = await pdf_downloader_tool_instance.execute(
            mock_agent_context_pdf_dl, 
            url=url, 
            folder=temp_dir_for_functional_pdf_downloader 
        )
        
    assert "PDF successfully downloaded and saved to" in result
    assert temp_dir_for_functional_pdf_downloader in result
    files = os.listdir(temp_dir_for_functional_pdf_downloader)
    assert len(files) == 1
    assert files[0].endswith('.pdf')

@pytest.mark.asyncio
async def test_pdf_dl_invalid_content_type(pdf_downloader_tool_instance: BaseTool, mock_agent_context_pdf_dl: AgentContext):
    url = 'https://example.com/not-a-pdf.html'
    mock_response = MagicMock(spec=requests.Response)
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {'Content-Type': 'text/html'}
    mock_response.raw = MagicMock(); mock_response.raw.closed = False
    mock_response.close = MagicMock()

    with patch('autobyteus.tools.pdf_downloader.requests.get', return_value=mock_response):
        result = await pdf_downloader_tool_instance.execute(mock_agent_context_pdf_dl, url=url)
    assert "The URL does not point to a PDF file. Content-Type: text/html" == result
    mock_response.close.assert_called_once()
