# Gemini PowerPoint Generator

This script generates PowerPoint presentations with AI-generated content using Gemini's capabilities. It creates a complete presentation with various types of content including:

- AI-generated images
- Architecture diagrams
- Data visualizations (charts)
- AI-generated tables

## Requirements

- Python 3.9+
- `python-pptx` library for PowerPoint generation
- Gemini API access configured in autobyteus

## Installation

Make sure you have the required dependencies:

```bash
pip install python-pptx
```

## Usage

Run the script with:

```bash
python gemini_pptx_generator.py "Your Presentation Title"
python gemini_pptx_slides.py "AI in healthcare" apyakurel@gmail.com
python powerpoint_generation_agent.py "AI in Healthcare" --output ./presentations/healthcare_ai.pptx --slides 2
```

### Command-line options:

- `title`: The title of your presentation (optional, defaults to "Gemini-Enhanced Presentation")
- `--output-dir`: Directory to save the PowerPoint file (default: ./presentations)
- `--save-content`: Save all generated content (images, diagrams) to the output directory

### Examples:

Generate a presentation with the default title:
```bash
python gemini_pptx_generator.py
```

Generate a presentation with a custom title:
```bash
python gemini_pptx_generator.py "AI in Healthcare"
```

Save the presentation in a specific directory:
```bash
python gemini_pptx_generator.py "AI in Healthcare" --output-dir ~/Documents/Presentations
```

Save all generated content (images, diagrams) along with the presentation:
```bash
python gemini_pptx_generator.py "AI in Healthcare" --save-content
```

## Features

1. **Title Slide**: Creates a professional title slide with AI-generated subtitle
2. **Agenda Slide**: Lists the content types included in the presentation
3. **AI-Generated Image**: Creates a slide with an AI-generated image based on a prompt
4. **Architecture Diagram**: Creates a slide with an AI-generated architecture diagram
5. **Data Visualization**: Creates a slide with an AI-generated chart or graph
6. **Data Table**: Creates a slide with an AI-generated data table
7. **Closing Slide**: Adds a professional closing slide

## Customization

You can modify the script to:

- Change the default prompts for image and diagram generation
- Add more slide types
- Adjust the styling of slides
- Add custom branding elements

## Limitations

- Video content is not included in the current version
- Some PowerPoint formatting options may be limited by the python-pptx library 