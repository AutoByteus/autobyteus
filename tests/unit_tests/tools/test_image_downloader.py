# File: tests/unit_tests/tools/test_image_downloader.py

import os
import asyncio
import aiohttp
import pytest
import tempfile
import shutil
import xml.sax.saxutils
from unittest.mock import patch, AsyncMock, MagicMock, Mock
from autobyteus.tools.image_downloader import ImageDownloader
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 

@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def temp_dir_for_image_downloader(): 
    temp_dir_path = tempfile.mkdtemp(prefix="img_dl_test_")
    yield temp_dir_path
    shutil.rmtree(temp_dir_path, ignore_errors=True)

def test_image_downloader_default_init_config(): 
    downloader = ImageDownloader() 
    assert downloader.download_folder == downloader.default_download_folder
    assert downloader.supported_formats == ['.jpeg', '.jpg', '.gif', '.png', '.webp'] 

def test_image_downloader_with_custom_instantiation_config(temp_dir_for_image_downloader):
    config = ToolConfig(params={'custom_download_folder': temp_dir_for_image_downloader})
    downloader = ImageDownloader(config=config)
    assert downloader.download_folder == temp_dir_for_image_downloader

def test_tool_state_initialization():
    """Tests that the tool_state attribute is properly initialized."""
    tool = ImageDownloader()
    assert hasattr(tool, 'tool_state')
    assert isinstance(tool.tool_state, dict)
    assert tool.tool_state == {}
    # Verify it's usable
    tool.tool_state['run_count'] = 1
    assert tool.tool_state['run_count'] == 1

def test_get_name():
    assert ImageDownloader.get_name() == "ImageDownloader"

def test_get_description():
    desc = ImageDownloader.get_description()
    assert "Downloads an image from a given URL." in desc
    for fmt in ImageDownloader.supported_formats:
        assert fmt.upper()[1:] in desc 

def test_get_config_schema_for_instantiation(): 
    schema = ImageDownloader.get_config_schema() 
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1
    
    param = schema.get_parameter('custom_download_folder')
    assert isinstance(param, ParameterDefinition)
    assert param.param_type == ParameterType.STRING
    assert not param.required
    assert param.default_value is None
    assert "default download folder" in param.description

def test_get_argument_schema_for_execution(): 
    schema = ImageDownloader.get_argument_schema() 
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 
    
    url_param = schema.get_parameter('url')
    assert isinstance(url_param, ParameterDefinition)
    assert url_param.name == "url"
    assert url_param.param_type == ParameterType.STRING
    assert url_param.required is True
    assert "direct URL to an image file" in url_param.description

    folder_param = schema.get_parameter('folder')
    assert isinstance(folder_param, ParameterDefinition)
    assert folder_param.name == "folder"
    assert folder_param.param_type == ParameterType.STRING
    assert folder_param.required is False
    assert "Optional. Custom directory path" in folder_param.description

@pytest.mark.asyncio 
async def test_execute_missing_url_arg(mock_agent_context):
    downloader = ImageDownloader()
    with pytest.raises(ValueError, match="Invalid arguments for tool 'ImageDownloader'"):
        await downloader.execute(mock_agent_context) 

@pytest.mark.asyncio
async def test_execute_unsupported_url_format(mock_agent_context):
    downloader = ImageDownloader()
    url_with_invalid_ext = 'https://example.com/file.txt' 
    
    with pytest.raises(ValueError, match="Unsupported image format"):
        await downloader.execute(mock_agent_context, url=url_with_invalid_ext)

@pytest.mark.asyncio
async def test_execute_success(temp_dir_for_image_downloader, mock_agent_context):
    downloader = ImageDownloader(config=ToolConfig(params={'custom_download_folder': temp_dir_for_image_downloader}))
    
    url = 'https://example.com/test.jpg'
    
    from PIL import Image as PillowImage
    from io import BytesIO
    img_byte_arr = BytesIO()
    PillowImage.new('RGB', (10, 10), color = 'red').save(img_byte_arr, format='JPEG')
    mock_image_data_valid_jpeg = img_byte_arr.getvalue()


    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=mock_image_data_valid_jpeg) 
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        result = await downloader.execute(mock_agent_context, url=url) 
            
        assert "The image is downloaded and stored at:" in result
        assert temp_dir_for_image_downloader in result 
        files = os.listdir(temp_dir_for_image_downloader)
        assert len(files) == 1
        assert files[0].endswith('.jpg')
        with open(os.path.join(temp_dir_for_image_downloader, files[0]), 'rb') as f:
            assert f.read() == mock_image_data_valid_jpeg

@pytest.mark.asyncio
async def test_execute_with_optional_folder_override(temp_dir_for_image_downloader, mock_agent_context):
    default_dl_folder = os.path.join(temp_dir_for_image_downloader, "default_dl")
    os.makedirs(default_dl_folder)
    downloader = ImageDownloader(config=ToolConfig(params={'custom_download_folder': str(default_dl_folder)}))
    
    override_dl_folder = os.path.join(temp_dir_for_image_downloader, "override_dl")

    url = 'https://example.com/another.png'
    
    from PIL import Image as PillowImage 
    from io import BytesIO
    img_byte_arr = BytesIO()
    PillowImage.new('RGB', (5,5)).save(img_byte_arr, format='PNG')
    mock_image_data_valid_png = img_byte_arr.getvalue()

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=mock_image_data_valid_png)
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
        result = await downloader.execute(mock_agent_context, url=url, folder=str(override_dl_folder))
            
        assert "The image is downloaded and stored at:" in result
        assert str(override_dl_folder) in result 
        assert str(default_dl_folder) not in result 
        
        files = os.listdir(override_dl_folder)
        assert len(files) == 1
        assert files[0].endswith('.png')
        assert not os.listdir(default_dl_folder)


@pytest.mark.asyncio
async def test_execute_network_aiohttp_client_error(mock_agent_context):
    downloader = ImageDownloader()
    url = 'https://nonexistent.example.com/test.jpg'
    
    with patch('aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__.return_value.get.side_effect = aiohttp.ClientConnectorError(Mock(), OSError("Test connection error"))
        
        with pytest.raises(ValueError, match="Error processing image from"):
            await downloader.execute(mock_agent_context, url=url)

@pytest.mark.asyncio
async def test_execute_unidentified_image_error(mock_agent_context, temp_dir_for_image_downloader):
    downloader = ImageDownloader(config=ToolConfig(params={'custom_download_folder': temp_dir_for_image_downloader}))
    url = 'https://example.com/not_an_image.jpg' 
    
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=b'this is not image data') 
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(ValueError, match="Error processing image from"):
            await downloader.execute(mock_agent_context, url=url)

def test_on_weibo_post_completed_removes_image(temp_dir_for_image_downloader):
    downloader = ImageDownloader(config=ToolConfig(params={'custom_download_folder': temp_dir_for_image_downloader}))
    
    dummy_image_path = os.path.join(temp_dir_for_image_downloader, "last_downloaded.png")
    with open(dummy_image_path, "w") as f:
        f.write("dummy")
    downloader.last_downloaded_image = dummy_image_path
    
    assert os.path.exists(dummy_image_path)
    
    downloader.on_weibo_post_completed() 
    
    assert not os.path.exists(dummy_image_path)
    assert downloader.last_downloaded_image is None

def test_on_weibo_post_completed_no_image(temp_dir_for_image_downloader):
    downloader = ImageDownloader(config=ToolConfig(params={'custom_download_folder': temp_dir_for_image_downloader}))
    downloader.last_downloaded_image = None 
    
    downloader.on_weibo_post_completed()
    assert downloader.last_downloaded_image is None

    downloader.last_downloaded_image = os.path.join(temp_dir_for_image_downloader, "non_existent.png")
    downloader.on_weibo_post_completed()
    assert downloader.last_downloaded_image is None
