import pytest
from pathlib import Path
import base64
from unittest.mock import mock_open, patch
from autobyteus.llm.utils.process_image import process_image, is_base64, is_valid_image_path

def test_process_image_with_bytes():
    test_bytes = b"test image bytes"
    expected_base64 = base64.b64encode(test_bytes).decode("utf-8")
    
    result = process_image(test_bytes)
    
    assert result["type"] == "image_url"
    assert result["image_url"] == f"data:image/jpeg;base64,{expected_base64}"

def test_process_image_with_valid_file_path(tmp_path):
    # Create a temporary test image file
    test_img = tmp_path / "test.jpg"
    test_img.write_bytes(b"test image content")
    
    with patch("builtins.open", mock_open(read_data=b"test image content")):
        result = process_image(str(test_img))
    
    assert result["type"] == "image_url"
    assert result["image_url"].startswith("data:image/jpeg;base64,")

def test_process_image_with_base64():
    test_base64 = base64.b64encode(b"test").decode("utf-8")
    
    result = process_image(test_base64)
    
    assert result["type"] == "image_url"
    assert result["image_url"] == f"data:image/jpeg;base64,{test_base64}"

def test_process_image_with_url():
    test_url = "https://example.com/image.jpg"
    
    result = process_image(test_url)
    
    assert result["type"] == "image_url"  
    assert result["image_url"] == test_url

def test_process_image_invalid_input():
    with pytest.raises(ValueError, match="Invalid image path or URL"):
        process_image("invalid_path.jpg")

def test_process_image_invalid_type():
    with pytest.raises(ValueError, match="Image input must be either bytes, file path, base64 string, or URL"):
        process_image(123)

def test_is_base64_valid():
    valid_base64 = base64.b64encode(b"test").decode("utf-8")
    assert is_base64(valid_base64) is True

def test_is_base64_invalid():
    assert is_base64("not-base64!") is False

def test_is_valid_image_path_valid(tmp_path):
    test_img = tmp_path / "test.jpg"
    test_img.write_bytes(b"test")
    assert is_valid_image_path(str(test_img)) is True

def test_is_valid_image_path_invalid():
    assert is_valid_image_path("nonexistent.jpg") is False
    assert is_valid_image_path("invalid.txt") is False