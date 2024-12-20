import asyncio
import os
import pytest
from PIL import Image, ImageDraw, ImageFont
from autobyteus.workflow.simple_task import SimpleTask
from autobyteus.llm.models import LLMModel

def create_test_image(path: str):
    """Create a simple test image with text and shapes."""
    # Create a new image with a white background
    image = Image.new('RGB', (400, 300), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw shapes
    draw.rectangle([50, 50, 150, 150], outline='blue', width=2)  # Blue square
    draw.ellipse([200, 50, 300, 150], outline='red', width=2)    # Red circle
    
    # Add text
    draw.text((100, 200), "Hello World!", fill='black')
    
    # Save the image
    image.save(path)
    return path

@pytest.mark.asyncio
async def test_image_analysis():
    """Test SimpleTask with image analysis."""
    # Setup
    test_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(test_dir, 'test_image.png')
    
    try:
        # Create test image
        create_test_image(image_path)
        
        # Create and execute task
        task = SimpleTask(
            name="test_image_analyzer",
            instruction="Please analyze this image and describe what you see. Include details about shapes, colors, and any text present.",
            llm_model=LLMModel.CLAUDE_3_SONNET_API,
            input_data=image_path
        )
        
        result = await task.execute()
        
        # Assertions
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Check for expected content in the response
        expected_keywords = ['square', 'circle', 'blue', 'red', 'Hello World']
        for keyword in expected_keywords:
            assert keyword.lower() in result.lower(), f"Expected to find '{keyword}' in the result"
            
    finally:
        # Cleanup
        if os.path.exists(image_path):
            os.remove(image_path)