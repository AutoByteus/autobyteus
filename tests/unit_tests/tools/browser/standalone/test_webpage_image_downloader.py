import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.webpage_image_downloader import WebPageImageDownloader
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry # Added
from autobyteus.tools.tool_state import ToolState

TOOL_NAME_IMG_DOWNLOADER = "WebPageImageDownloader"

@pytest.fixture
def mock_agent_context_img_dl():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_img_dl_standalone"
    return mock_context

@pytest.fixture
def img_downloader_tool_instance(mock_agent_context_img_dl):
    tool = WebPageImageDownloader()
    tool.set_agent_id(mock_agent_context_img_dl.agent_id)
    return tool

def test_tool_state_initialization(img_downloader_tool_instance: WebPageImageDownloader):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(img_downloader_tool_instance, 'tool_state')
    assert isinstance(img_downloader_tool_instance.tool_state, ToolState)
    assert img_downloader_tool_instance.tool_state == {}
    # Verify it's usable
    img_downloader_tool_instance.tool_state['download_log'] = []
    assert img_downloader_tool_instance.tool_state['download_log'] == []

# Definition Tests
def test_img_downloader_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_IMG_DOWNLOADER) # Using default_tool_registry
    assert definition is not None
    assert definition.name == TOOL_NAME_IMG_DOWNLOADER
    assert "Downloads all usable images" in definition.description

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
async def test_execute_success(img_downloader_tool_instance: WebPageImageDownloader, mock_agent_context_img_dl, tmp_path):
    page_url = "https://example.com/gallery"
    save_directory = tmp_path / "downloaded_images"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.evaluate.return_value = [
        "images/pic1.jpg", 
        "https://othersite.com/pic2.png", 
        "images/pic3.svg", 
        "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", 
        "//cdn.example.com/pic4.jpeg" 
    ]
    mock_playwright_page.url = page_url 

    async def mock_page_request_get(url_to_get):
        mock_img_resp = AsyncMock()
        if "pic1.jpg" in url_to_get or "pic2.png" in url_to_get or "pic4.jpeg" in url_to_get : 
            mock_img_resp.ok = True
            mock_img_resp.body.return_value = b"fake_image_bytes_" + os.path.basename(url_to_get).encode()
        else:
            mock_img_resp.ok = False
            mock_img_resp.status = 404
        return mock_img_resp
    
    mock_playwright_page.request = AsyncMock()
    mock_playwright_page.request.get = AsyncMock(side_effect=mock_page_request_get)


    with patch.object(img_downloader_tool_instance, 'initialize', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'close', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        saved_file_paths = await img_downloader_tool_instance.execute(
            mock_agent_context_img_dl, 
            url=page_url, 
            save_dir=str(save_directory)
        )
    
    assert len(saved_file_paths) == 3 
    assert os.path.isdir(save_directory)
    
    expected_files = ["pic1.jpg", "pic2.png", "pic4.jpeg"]
    downloaded_filenames = [os.path.basename(p) for p in saved_file_paths]

    for expected_file_part in expected_files:
        assert any(expected_file_part in fname for fname in downloaded_filenames), f"Expected part {expected_file_part} not in downloaded filenames: {downloaded_filenames}"
        for p in saved_file_paths:
            if expected_file_part in p:
                 with open(p, "rb") as f:
                    assert f.read() == b"fake_image_bytes_" + expected_file_part.encode()


@pytest.mark.asyncio
async def test_execute_invalid_page_url(img_downloader_tool_instance: WebPageImageDownloader, mock_agent_context_img_dl, tmp_path):
    with pytest.raises(ValueError, match="Invalid page URL format"):
        await img_downloader_tool_instance.execute(
            mock_agent_context_img_dl, 
            url="not_a_valid_url", 
            save_dir=str(tmp_path)
        )

@pytest.mark.asyncio
async def test_execute_no_images_found(img_downloader_tool_instance: WebPageImageDownloader, mock_agent_context_img_dl, tmp_path):
    page_url = "https://example.com/no_images_page"
    save_directory = tmp_path / "empty_images"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.evaluate.return_value = [] 
    mock_playwright_page.url = page_url

    with patch.object(img_downloader_tool_instance, 'initialize', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'close', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        saved_file_paths = await img_downloader_tool_instance.execute(
            mock_agent_context_img_dl,
            url=page_url,
            save_dir=str(save_directory)
        )
    
    assert len(saved_file_paths) == 0
    assert os.path.isdir(save_directory) 


@pytest.mark.asyncio
async def test_execute_image_download_error(img_downloader_tool_instance: WebPageImageDownloader, mock_agent_context_img_dl, tmp_path):
    page_url = "https://example.com/gallery_with_error"
    save_directory = tmp_path / "error_images"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.evaluate.return_value = ["image_that_will_fail.jpg"]
    mock_playwright_page.url = page_url
    
    mock_playwright_page.request = AsyncMock()
    mock_playwright_page.request.get = AsyncMock(side_effect=Exception("Simulated download failure"))

    with patch.object(img_downloader_tool_instance, 'initialize', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'close', AsyncMock()), \
         patch.object(img_downloader_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        saved_file_paths = await img_downloader_tool_instance.execute(
            mock_agent_context_img_dl,
            url=page_url,
            save_dir=str(save_directory)
        )
    
    assert len(saved_file_paths) == 0 
