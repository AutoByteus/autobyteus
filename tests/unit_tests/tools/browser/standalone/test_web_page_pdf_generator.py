import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.web_page_pdf_generator import WebPagePDFGenerator
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_state import ToolState

TOOL_NAME_PDF_GENERATOR = "WebPagePDFGenerator"

@pytest.fixture
def mock_agent_context_pdf_gen():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_pdf_gen_standalone"
    return mock_context

@pytest.fixture
def pdf_generator_tool_instance(mock_agent_context_pdf_gen):
    tool = WebPagePDFGenerator()
    tool.set_agent_id(mock_agent_context_pdf_gen.agent_id)
    return tool

def test_tool_state_initialization(pdf_generator_tool_instance: WebPagePDFGenerator):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(pdf_generator_tool_instance, 'tool_state')
    assert isinstance(pdf_generator_tool_instance.tool_state, ToolState)
    assert pdf_generator_tool_instance.tool_state == {}
    # Verify it's usable
    pdf_generator_tool_instance.tool_state['pdf_count'] = 1
    assert pdf_generator_tool_instance.tool_state['pdf_count'] == 1

# Definition Tests
def test_pdf_generator_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_PDF_GENERATOR)
    assert definition is not None
    assert definition.name == TOOL_NAME_PDF_GENERATOR
    assert "Generates a PDF (A4 format)" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 # url, save_dir
    param_url = schema.get_parameter("url")
    assert param_url is not None
    assert param_url.required is True
    param_save_dir = schema.get_parameter("save_dir")
    assert param_save_dir is not None
    assert param_save_dir.param_type == ParameterType.STRING 
    assert param_save_dir.required is True

# Execute Tests
@pytest.mark.asyncio
async def test_execute_pdf_generation_success(pdf_generator_tool_instance: WebPagePDFGenerator, mock_agent_context_pdf_gen, tmp_path):
    url_to_pdf = "https://example.com/report"
    save_directory = tmp_path / "generated_pdfs"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.pdf = AsyncMock()

    with patch.object(pdf_generator_tool_instance, 'initialize', AsyncMock()) as mock_init, \
         patch.object(pdf_generator_tool_instance, 'close', AsyncMock()) as mock_close, \
         patch.object(pdf_generator_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        returned_path = await pdf_generator_tool_instance.execute(
            mock_agent_context_pdf_gen, 
            url=url_to_pdf, 
            save_dir=str(save_directory)
        )
    
    mock_init.assert_called_once()
    mock_playwright_page.goto.assert_called_once_with(url_to_pdf, wait_until="networkidle", timeout=60000)
    
    assert mock_playwright_page.pdf.call_count == 1
    call_args = mock_playwright_page.pdf.call_args
    assert call_args is not None
    assert call_args[1]['format'] == 'A4' 
    assert call_args[1]['print_background'] is True
    generated_pdf_path_arg = call_args[1]['path'] 
    
    assert os.path.dirname(generated_pdf_path_arg) == str(save_directory)
    assert generated_pdf_path_arg.endswith(".pdf")
    assert returned_path == os.path.abspath(generated_pdf_path_arg)
    mock_close.assert_called_once()

@pytest.mark.asyncio
async def test_execute_invalid_url(pdf_generator_tool_instance: WebPagePDFGenerator, mock_agent_context_pdf_gen, tmp_path):
    with pytest.raises(ValueError, match="Invalid page URL format"):
        await pdf_generator_tool_instance.execute(
            mock_agent_context_pdf_gen, 
            url="badurl", 
            save_dir=str(tmp_path)
        )

@pytest.mark.asyncio
async def test_execute_playwright_error(pdf_generator_tool_instance: WebPagePDFGenerator, mock_agent_context_pdf_gen, tmp_path):
    url_to_pdf = "https://example.com/error-page"
    save_directory = tmp_path / "pdf_errors"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.goto = AsyncMock(side_effect=Exception("Playwright PDF goto failed"))

    with patch.object(pdf_generator_tool_instance, 'initialize', AsyncMock()), \
         patch.object(pdf_generator_tool_instance, 'close', AsyncMock()) as mock_close, \
         patch.object(pdf_generator_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        with pytest.raises(RuntimeError, match="WebPagePDFGenerator failed for URL .* Playwright PDF goto failed"):
            await pdf_generator_tool_instance.execute(
                mock_agent_context_pdf_gen, 
                url=url_to_pdf, 
                save_dir=str(save_directory)
            )
        mock_close.assert_called_once()
