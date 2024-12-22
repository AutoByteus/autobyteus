import os
import base64
from autobyteus.llm.utils.process_image import process_image
from pathlib import Path
import pytest

TEST_IMAGE_PATH = str(
    Path(__file__).parent.parent.parent.parent / "resources" / "image_1.jpg"
)


def test_process_image_with_bytes():
    sample_bytes = b"fake_image_data"
    result = process_image(sample_bytes)
    assert result["type"] == "image_url"
    assert "base64" in result["image_url"]["url"]


def test_process_image_with_file_path():
    result = process_image(TEST_IMAGE_PATH)
    assert result["type"] == "image_url"
    assert "data:image/" in result["image_url"]["url"]


def test_process_image_with_base64():
    sample_base64 = base64.b64encode(b"fake_image_data").decode("utf-8")
    result = process_image(sample_base64)
    assert result["type"] == "image_url"
    assert "base64" in result["image_url"]["url"]


def test_process_image_with_url():
    sample_url = "http://example.com/fake_image.png"
    result = process_image(sample_url)
    assert result["type"] == "image_url"
    assert result["image_url"]["url"] == sample_url
