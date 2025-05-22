import os
import asyncio
import pytest
import tempfile
import shutil
from unittest.mock import patch, AsyncMock, MagicMock, Mock # Added Mock
from autobyteus.tools.image_downloader import ImageDownloader
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
async def test_image_downloader_default_config():
    downloader = ImageDownloader()
    assert downloader.download_folder == downloader.default_download_folder
    assert downloader.supported_formats == ['.jpeg', '.jpg', '.gif', '.png', '.webp']

@pytest.mark.asyncio
async def test_image_downloader_with_custom_config(temp_dir):
    config = ToolConfig(params={'custom_download_folder': temp_dir})
    downloader = ImageDownloader(config=config)
    assert downloader.download_folder == temp_dir

@pytest.mark.asyncio
async def test_get_config_schema(): # Removed mock_agent_context as it's a class method test
    schema = ImageDownloader.get_config_schema()
    assert len(schema) == 1
    
    param = schema.get_parameter('custom_download_folder')
    assert param is not None
    assert param.param_type == ParameterType.DIRECTORY_PATH
    assert not param.required
    assert param.default_value is None

@pytest.mark.asyncio
async def test_tool_usage_xml(): # Removed mock_agent_context as it's a class method test
    expected_formats = ['.jpeg', '.jpg', '.gif', '.png', '.webp']
    usage = ImageDownloader.tool_usage_xml()
    
    assert 'ImageDownloader: Downloads an image from a given URL.' in usage
    assert '<command name="ImageDownloader">' in usage
    assert '<arg name="url">image_url</arg>' in usage
    
    # Check that all supported formats are mentioned
    for fmt in expected_formats:
        assert fmt in usage

@pytest.mark.asyncio 
async def test_execute_missing_url(mock_agent_context): # Added mock_agent_context
    downloader = ImageDownloader()
    
    with pytest.raises(ValueError, match="The 'url' keyword argument must be specified."):
        await downloader.execute(mock_agent_context) # Added mock_agent_context

@pytest.mark.asyncio
async def test_execute_unsupported_format(mock_agent_context): # Added mock_agent_context
    downloader = ImageDownloader()
    url = 'https://example.com/file.txt'
    
    with pytest.raises(ValueError, match="Unsupported image format"):
        await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context

@pytest.mark.asyncio
async def test_execute_success_mock(temp_dir, mock_agent_context): # Added mock_agent_context
    config = ToolConfig(params={'custom_download_folder': temp_dir})
    downloader = ImageDownloader(config=config)
    
    url = 'https://example.com/test.jpg'
    mock_image_data = b'fake_image_data'
    
    with patch('aiohttp.ClientSession') as mock_session:
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=mock_image_data)
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        # Mock PIL Image
        with patch('autobyteus.tools.image_downloader.Image') as mock_image:
            mock_img = MagicMock()
            mock_img.format = 'JPEG' # Ensure Pillow recognizes the format
            # Pillow's open context manager returns the image object itself
            mock_image.open.return_value.__enter__.return_value = mock_img 
            
            result = await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
            
            assert "The image is downloaded and stored at:" in result
            assert temp_dir in result
            # Verify file was created
            files = os.listdir(temp_dir)
            assert len(files) == 1
            assert files[0].endswith('.jpg')


@pytest.mark.asyncio
async def test_execute_network_error(mock_agent_context): # Added mock_agent_context
    downloader = ImageDownloader()
    url = 'https://nonexistent.example.com/test.jpg'
    
    with patch('aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
        
        with pytest.raises(ValueError, match="Error processing image"): # The tool wraps exceptions into ValueError
            await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context

def test_get_name():
    assert ImageDownloader.get_name() == "ImageDownloader"

@pytest.mark.asyncio
async def test_supported_formats_validation(mock_agent_context): # Added mock_agent_context
    downloader = ImageDownloader()
    
    # Test each supported format
    supported_urls = [
        'https://example.com/test.jpeg',
        'https://example.com/test.jpg', 
        'https://example.com/test.gif',
        'https://example.com/test.png',
        'https://example.com/test.webp'
    ]
    
    for url in supported_urls:
        # Should not raise ValueError for supported formats
        try:
            # This will fail at network level, but format validation should pass
            # Mock network to avoid actual calls just for format validation
            with patch('aiohttp.ClientSession') as mock_session:
                mock_http_response = AsyncMock()
                mock_http_response.raise_for_status = MagicMock()
                mock_http_response.read = AsyncMock(return_value=b'fake_data')
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_http_response
                
                with patch('autobyteus.tools.image_downloader.Image') as mock_pil_image:
                    mock_img_obj = MagicMock()
                    mock_img_obj.format = 'JPEG' # Dummy format
                    mock_pil_image.open.return_value.__enter__.return_value = mock_img_obj
                    await downloader.execute(mock_agent_context, url=url) # Added mock_agent_context
        except ValueError as e:
            # Should not be a format error
            assert "Unsupported image format" not in str(e), f"Format validation failed for {url}"
        except Exception:
            # Other exceptions (like network mock issues if not perfectly set up) are fine for this test's focus
            pass

@pytest.mark.asyncio
async def test_custom_folder_parameter(temp_dir, mock_agent_context): # Added mock_agent_context
    downloader = ImageDownloader() # Default config, folder passed via execute
    url = 'https://example.com/test.jpg'
    
    with patch('aiohttp.ClientSession') as mock_session, \
         patch('autobyteus.tools.image_downloader.Image') as mock_image:
        
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=b'fake_image_data')
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        mock_img = MagicMock()
        mock_img.format = 'JPEG'
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        result = await downloader.execute(mock_agent_context, url=url, folder=temp_dir) # Added mock_agent_context
        
        assert temp_dir in result
        # Verify file was created in custom folder
        files = os.listdir(temp_dir)
        assert len(files) == 1
        assert files[0].endswith('.jpg')
