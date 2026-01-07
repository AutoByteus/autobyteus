# file: autobyteus/autobyteus/tools/usage/formatters/patch_file_xml_example_formatter.py
"""
XML Example formatter for the patch_file tool using standard <tool name="patch_file"> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class PatchFileXmlExampleFormatter(BaseExampleFormatter):
    """
    Formats usage examples for patch_file using the standard <tool name="patch_file"> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates usage examples for patch_file.
        """
        return '''### Example 1: Modify a function in a Python file

<tool name="patch_file">
    <arguments>
        <arg name="path">/path/to/utils.py</arg>
        <arg name="patch">
__START_PATCH__
--- a/utils.py
+++ b/utils.py
@@ -10,7 +10,7 @@
 def calculate_total(items):
     """Calculate the total price of items."""
     total = 0
-    for item in items:
+    for item in sorted(items, key=lambda x: x.price):
         total += item.price
     return total
__END_PATCH__
        </arg>
    </arguments>
</tool>

### Example 2: Add new lines to a configuration file

<tool name="patch_file">
    <arguments>
        <arg name="path">config/settings.yaml</arg>
        <arg name="patch">
__START_PATCH__
--- a/settings.yaml
+++ b/settings.yaml
@@ -5,3 +5,6 @@
 logging:
   level: INFO
   format: "%(asctime)s - %(message)s"
+
+cache:
+  enabled: true
+  ttl: 3600
__END_PATCH__
        </arg>
    </arguments>
</tool>'''
