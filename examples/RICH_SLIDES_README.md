# Rich Google Slides Example

This example demonstrates how to create feature-rich Google Slides presentations programmatically using the Google Slides API. The script creates a presentation with multiple slides containing various visual elements like:

- Title slides with formatted text
- Agenda slides with bullet points
- Charts (linked from Google Sheets)
- Workflow diagrams with shapes and connecting lines
- Data tables with formatted content

## Prerequisites

1. Make sure you have the Google Slides MCP server running
2. You need Google authentication set up with appropriate permissions
3. Python 3.7+ with asyncio support

## Installation

No additional installation is needed beyond the standard autobyteus package setup.

## Usage

Run the script with your Google email address:

```bash
python rich_slides_example.py your.email@gmail.com [optional_title]
python rich_slides_example.py apyakurel@gmail.com "comprehensive AI driven STEM education platform for students and teachers"
```

### Parameters:

- `your.email@gmail.com` - Your Google account email (required)
- `optional_title` - Custom presentation title (optional, defaults to "Rich Presentation Demo")

## Features Demonstrated

### 1. Multi-Slide Creation

The script creates a presentation with 5 different slides, each demonstrating different capabilities:

- Title slide
- Agenda slide with bullet points
- Chart slide (with instructions for embedding Google Sheets charts)
- Workflow diagram slide with shapes and connecting lines
- Data table slide with formatted content

### 2. Visualizations

#### Charts from Google Sheets

To embed actual charts from Google Sheets, you need:
1. A Google Sheet with a chart already created
2. The spreadsheet ID and chart ID

The script shows the structure for the `createSheetsChart` request:

```python
{
    "createSheetsChart": {
        "objectId": "chart1",
        "spreadsheetId": "your_spreadsheet_id",
        "chartId": your_chart_id,
        "linkingMode": "LINKED",
        "elementProperties": {
            "pageObjectId": "slide_id",
            "size": {
                "height": {"magnitude": 4000000, "unit": "EMU"},
                "width": {"magnitude": 4000000, "unit": "EMU"}
            },
            "transform": {
                "scaleX": 1,
                "scaleY": 1,
                "translateX": 1000000,
                "translateY": 2000000,
                "unit": "EMU"
            }
        }
    }
}
```

#### Workflow Diagrams

The script demonstrates creating workflow diagrams by:
1. Creating rectangular shapes for each step
2. Adding text to each shape
3. Creating connecting lines between shapes

#### Data Tables

The script shows how to:
1. Create a table with specified rows and columns
2. Add text to individual cells
3. Format table content

## Understanding EMU Units

The Google Slides API uses EMU (English Metric Units) for positioning and sizing elements:
- 1 inch = 914400 EMU
- 1 cm = 360000 EMU
- 1 point = 12700 EMU

## Extending the Example

You can extend this example to create even more complex presentations:

1. **Advanced Charts**: Create more sophisticated charts in Google Sheets and embed them
2. **Custom Shapes**: Use different shape types (circles, arrows, etc.) for more complex diagrams
3. **Images**: Add images to slides using the `createImage` request
4. **Animations**: Apply animations to elements (though this requires more advanced API usage)
5. **Speaker Notes**: Add speaker notes to slides

## Troubleshooting

If you encounter issues:

1. Make sure the Google Slides MCP server is running at `ws://localhost:8765`
2. Check that your Google account has appropriate permissions
3. Verify that you're using the correct email address
4. Check the logs for detailed error messages

## Additional Resources

- [Google Slides API Documentation](https://developers.google.com/slides/api/guides/overview)
- [Batch Update Reference](https://developers.google.com/slides/api/reference/rest/v1/presentations/batchUpdate)
- [EMU Units Explanation](https://developers.google.com/slides/api/guides/concepts#units) 