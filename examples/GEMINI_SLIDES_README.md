# Gemini-Enhanced Google Slides

This example demonstrates how to use Gemini's powerful image, diagram, and video generation capabilities to create visually rich Google Slides presentations.

## Features

- Generate realistic images for slides using Gemini's Imagen model
- Create professional diagrams and charts with natural language descriptions
- Generate videos to embed in presentations
- Automatically embed generated content in Google Slides

## Requirements

1. Google API credentials (set as environment variables)
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REFRESH_TOKEN`
   
2. Gemini API key
   - `GEMINI_API_KEY`

3. Python packages
   - `google-generativeai`
   - `websockets`
   - `google-auth`
   - `google-api-python-client`
   - `pillow`

## Getting Started

1. Set up the Google Slides MCP server:
   ```bash
   python test_google_slides_mcp_script.py --transport websocket
   ```

2. In another terminal, run the Gemini Slides example:
   ```bash
   # Basic usage
   python gemini_slides_example.py your.google@email.com "My Presentation Title"
   
   # Run in dry-run mode (generate content but don't create slides)
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --dry-run
   
   # Use a custom base URL for serving images (needed for public access)
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --base-url "https://your-public-server.com"
   
   # Save the presentation as a PowerPoint file locally
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --save-ppt
   
   # Specify output directory for the PowerPoint file
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --save-ppt --output-dir "./presentations"
   
   # Save all generated content (images, videos) to the output directory
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --save-content
   
   # Complete example with all options
   python gemini_slides_example.py your.google@email.com "My Presentation Title" --dry-run --save-ppt --save-content --output-dir "./my_presentations"
   ```

### Note on Image URLs

Google Slides requires that images be accessible via public URLs. When running locally, the script starts a temporary web server to host generated images, but these URLs are only accessible from your local machine. For a real deployment, you'll need to:

1. Use the `--base-url` parameter to specify a publicly accessible server
2. Ensure the generated files are uploaded to that server
3. Or use a service like Firebase Storage, AWS S3, or similar to host the images

## How It Works

1. The script connects to the Google Slides MCP server via WebSocket
2. It creates a new blank presentation
3. For each slide, it:
   - Generates content (image/diagram/video) using the appropriate Gemini API
   - Saves the generated content to a locally served file
   - Creates a slide in the presentation with a reference to the content
   - Adds appropriate titles and formatting

## Slide Types

1. Title Slide
2. AI-Generated Future City Image
3. Architecture Diagram
4. Data Visualization/Chart
5. Visual Metaphor Illustration
6. Video Slide

## Custom Implementation

- The `GeminiLLM` class has been extended with methods for generating images, diagrams, and videos
- A temporary file server is set up to host the generated content, making it accessible to the Google Slides API
- Robust error handling includes graceful fallbacks when generation fails 