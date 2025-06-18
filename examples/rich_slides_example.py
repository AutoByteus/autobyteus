#!/usr/bin/env python3
"""
Rich Google Slides Example
This script demonstrates how to create a presentation with multiple slides
containing various visual elements like charts, diagrams, and more.
"""
import asyncio
import sys
import os
from pathlib import Path
import json
import logging

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("rich_slides_example")

async def create_rich_presentation(user_email, title="Rich Presentation Demo"):
    """
    Creates a presentation with multiple slides containing various visual elements.
    
    Args:
        user_email (str): The user's Google email address
        title (str): The title for the presentation
    """
    from autobyteus.tools.mcp import McpConfigService, McpConnectionManager

    # Set up MCP components
    logger.info("Setting up MCP connection...")
    config_service = McpConfigService()
    conn_manager = McpConnectionManager(config_service=config_service)
    
    # Configure the MCP server
    server_id = "google-slides-mcp-ws"
    mcp_config = {
        server_id: {
            "transport_type": "websocket",
            "uri": "ws://localhost:8765",
            "enabled": True,
            "tool_name_prefix": "gslides",
        }
    }
    config_service.load_configs(mcp_config)
    
    try:
        # Connect to MCP server
        session = await conn_manager.get_session(server_id)
        await session.transport_strategy.connect()
        
        # Step 1: Create a new presentation
        logger.info(f"Creating presentation with title: {title}")
        create_result = await session.transport_strategy.rpc_call(
            "tools/call",
            {
                "tool_name": "create_presentation", 
                "parameters": {
                    "user_google_email": user_email, 
                    "title": title
                }
            }
        )
        
        # Extract presentation ID from the result
        presentation_id = create_result.get("presentationId")
        
        if not presentation_id:
            logger.error("Failed to extract presentation ID")
            return
        
        logger.info(f"Created presentation with ID: {presentation_id}")
        
        # Step 2: Add slides with various content
        await create_title_slide(session, presentation_id, user_email, title)
        await create_agenda_slide(session, presentation_id, user_email)
        await create_chart_slide(session, presentation_id, user_email)
        await create_diagram_slide(session, presentation_id, user_email)
        await create_data_table_slide(session, presentation_id, user_email)
        
        logger.info(f"Rich presentation created successfully! ID: {presentation_id}")
        print(f"\nPresentation URL: https://docs.google.com/presentation/d/{presentation_id}/edit")
        
    except Exception as e:
        logger.error(f"Error creating rich presentation: {e}", exc_info=True)
    finally:
        # Clean up
        if conn_manager:
            await conn_manager.cleanup()

async def create_title_slide(session, presentation_id, user_email, title):
    """Creates a title slide with a heading and subtitle"""
    logger.info("Creating title slide...")
    
    # Create batch update requests for title slide
    requests = [
        # Create a new slide (first slide after the default one)
        {
            "createSlide": {
                "objectId": "titleSlide",
                "insertionIndex": 1,
                "slideLayoutReference": {
                    "predefinedLayout": "TITLE"
                }
            }
        },
        # Add title text by creating a title shape first
        {
            "createShape": {
                "objectId": "titleTextBox",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "titleSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 1500000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1500000,
                        "translateY": 1500000,
                        "unit": "EMU"
                    }
                }
            }
        },
        # Add text to the title shape
        {
            "insertText": {
                "objectId": "titleTextBox",
                "text": title
            }
        },
        # Add subtitle text
        {
            "createShape": {
                "objectId": "titleSubtitle",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "titleSlide",
                    "size": {
                        "width": {"magnitude": 5000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1500000,
                        "translateY": 3000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "titleSubtitle",
                "text": "Created with Google Slides API"
            }
        },
        # Add formatting to make the title stand out
        {
            "updateTextStyle": {
                "objectId": "titleTextBox",
                "style": {
                    "fontSize": {
                        "magnitude": 36,
                        "unit": "PT"
                    },
                    "foregroundColor": {
                        "opaqueColor": {
                            "rgbColor": {
                                "red": 0.2,
                                "green": 0.2,
                                "blue": 0.6
                            }
                        }
                    },
                    "bold": True
                },
                "textRange": {
                    "type": "ALL"
                },
                "fields": "fontSize,foregroundColor,bold"
            }
        }
    ]
    
    # Apply the batch update
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": requests
            }
        }
    )

async def create_agenda_slide(session, presentation_id, user_email):
    """Creates an agenda slide with bullet points"""
    logger.info("Creating agenda slide...")
    
    requests = [
        # Create a new slide
        {
            "createSlide": {
                "objectId": "agendaSlide",
                "insertionIndex": 2
            }
        },
        # Add title
        {
            "createShape": {
                "objectId": "agendaTitle",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "agendaSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1000000,
                        "translateY": 1000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "agendaTitle",
                "text": "Presentation Agenda"
            }
        },
        # Add bullet points
        {
            "createShape": {
                "objectId": "agendaBullets",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "agendaSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 4000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1500000,
                        "translateY": 2500000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "agendaBullets",
                "text": "1. Introduction\n2. Data Visualization\n3. Charts & Graphs\n4. Workflow Diagrams\n5. Conclusion"
            }
        },
        # Create bullets
        {
            "createParagraphBullets": {
                "objectId": "agendaBullets",
                "textRange": {
                    "type": "ALL"
                },
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
            }
        }
    ]
    
    # Apply the batch update
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": requests
            }
        }
    )

async def create_chart_slide(session, presentation_id, user_email):
    """Creates a slide with a chart from Google Sheets"""
    logger.info("Creating chart slide...")
    
    # Note: To embed a chart from Google Sheets, you need to:
    # 1. Have a Google Sheet with a chart already created
    # 2. Know the spreadsheet ID and chart ID
    
    # For this example, we'll create a placeholder with instructions
    requests = [
        # Create a new slide
        {
            "createSlide": {
                "objectId": "chartSlide",
                "insertionIndex": 3
            }
        },
        # Add title
        {
            "createShape": {
                "objectId": "chartTitle",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "chartSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1000000,
                        "translateY": 1000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "chartTitle",
                "text": "Data Visualization with Charts"
            }
        },
        # Add chart placeholder
        {
            "createShape": {
                "objectId": "chartPlaceholder",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "chartSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 4000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1500000,
                        "translateY": 2500000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "chartPlaceholder",
                "text": "To embed a real chart from Google Sheets:\n\n1. Create a chart in Google Sheets\n2. Use the createSheetsChart request with:\n   - spreadsheetId\n   - chartId\n   - linkingMode: 'LINKED'"
            }
        }
    ]
    
    # Apply the batch update
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": requests
            }
        }
    )

async def create_diagram_slide(session, presentation_id, user_email):
    """Creates a slide with a workflow diagram using shapes and lines"""
    logger.info("Creating diagram slide...")
    
    requests = [
        # Create a new slide
        {
            "createSlide": {
                "objectId": "diagramSlide",
                "insertionIndex": 4
            }
        },
        # Add title
        {
            "createShape": {
                "objectId": "diagramTitle",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1000000,
                        "translateY": 1000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "diagramTitle",
                "text": "Workflow Diagram"
            }
        },
        # Create first box in workflow
        {
            "createShape": {
                "objectId": "step1",
                "shapeType": "RECTANGLE",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 2000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1000000,
                        "translateY": 3000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "step1",
                "text": "Step 1"
            }
        },
        # Create second box
        {
            "createShape": {
                "objectId": "step2",
                "shapeType": "RECTANGLE",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 2000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 4000000,
                        "translateY": 3000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "step2",
                "text": "Step 2"
            }
        },
        # Create third box
        {
            "createShape": {
                "objectId": "step3",
                "shapeType": "RECTANGLE",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 2000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 7000000,
                        "translateY": 3000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "step3",
                "text": "Step 3"
            }
        },
        # Create connecting line 1
        {
            "createLine": {
                "objectId": "line1",
                "lineCategory": "STRAIGHT",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 1000000, "unit": "EMU"},
                        "height": {"magnitude": 10000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 3000000,
                        "translateY": 3500000,
                        "unit": "EMU"
                    }
                }
            }
        },
        # Create connecting line 2
        {
            "createLine": {
                "objectId": "line2",
                "lineCategory": "STRAIGHT",
                "elementProperties": {
                    "pageObjectId": "diagramSlide",
                    "size": {
                        "width": {"magnitude": 1000000, "unit": "EMU"},
                        "height": {"magnitude": 10000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 6000000,
                        "translateY": 3500000,
                        "unit": "EMU"
                    }
                }
            }
        }
    ]
    
    # Apply the batch update
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": requests
            }
        }
    )

async def create_data_table_slide(session, presentation_id, user_email):
    """Creates a slide with a data table"""
    logger.info("Creating data table slide...")
    
    requests = [
        # Create a new slide
        {
            "createSlide": {
                "objectId": "tableSlide",
                "insertionIndex": 5
            }
        },
        # Add title
        {
            "createShape": {
                "objectId": "tableTitle",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "tableSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1000000,
                        "translateY": 1000000,
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": "tableTitle",
                "text": "Data Table Example"
            }
        },
        # Create a table
        {
            "createTable": {
                "objectId": "dataTable",
                "rows": 4,
                "columns": 3,
                "elementProperties": {
                    "pageObjectId": "tableSlide",
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 3000000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 1500000,
                        "translateY": 2500000,
                        "unit": "EMU"
                    }
                }
            }
        }
    ]
    
    # Apply the batch update to create the table
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": requests
            }
        }
    )
    
    # Now add content to the table cells
    # Table headers
    table_headers = [
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 0,
                    "columnIndex": 0
                },
                "text": "Category"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 0,
                    "columnIndex": 1
                },
                "text": "Value 1"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 0,
                    "columnIndex": 2
                },
                "text": "Value 2"
            }
        }
    ]
    
    # Table data
    table_data = [
        # Row 1
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 1,
                    "columnIndex": 0
                },
                "text": "Product A"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 1,
                    "columnIndex": 1
                },
                "text": "45"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 1,
                    "columnIndex": 2
                },
                "text": "62"
            }
        },
        # Row 2
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 2,
                    "columnIndex": 0
                },
                "text": "Product B"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 2,
                    "columnIndex": 1
                },
                "text": "78"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 2,
                    "columnIndex": 2
                },
                "text": "51"
            }
        },
        # Row 3
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 3,
                    "columnIndex": 0
                },
                "text": "Product C"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 3,
                    "columnIndex": 1
                },
                "text": "36"
            }
        },
        {
            "insertText": {
                "objectId": "dataTable",
                "cellLocation": {
                    "rowIndex": 3,
                    "columnIndex": 2
                },
                "text": "93"
            }
        }
    ]
    
    # Apply the batch update for table content
    await session.transport_strategy.rpc_call(
        "tools/call",
        {
            "tool_name": "batch_update_presentation",
            "parameters": {
                "user_google_email": user_email,
                "presentation_id": presentation_id,
                "requests": table_headers + table_data
            }
        }
    )

async def main():
    """Main function to run the example"""
    if len(sys.argv) < 2:
        print("Usage: python rich_slides_example.py <user_google_email> [title]")
        sys.exit(1)
        
    user_email = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Rich Presentation Demo"
    
    await create_rich_presentation(user_email, title)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        sys.exit(1) 