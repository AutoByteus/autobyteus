# file: autobyteus/tests/unit_tests/tools/mcp/transport_strategies/test_base_client_strategy.py
import pytest
from autobyteus.tools.mcp.transport_strategies import McpTransportClientStrategy

def test_mcp_transport_client_strategy_is_abc():
    # Check if it's an ABC by trying to instantiate it, which should fail
    with pytest.raises(TypeError, match="Can't instantiate abstract class McpTransportClientStrategy with abstract method establish_connection"):
        McpTransportClientStrategy() # type: ignore

    # Check if it has the abstract method
    assert 'establish_connection' in McpTransportClientStrategy.__abstractmethods__
