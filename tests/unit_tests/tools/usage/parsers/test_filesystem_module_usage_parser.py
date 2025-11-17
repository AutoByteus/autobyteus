from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.tools.usage.parsers.filesystem_module_usage_parser import FilesystemModuleUsageParser


def test_parse_single_module_block():
    parser = FilesystemModuleUsageParser()
    content = """
    Some reasoning text.
    [RUN_MODULE]
    {"name": "image_gen", "args": {"prompt": "hi"}}
    [/RUN_MODULE]
    """
    response = CompleteResponse(content=content)

    invocations = parser.parse(response)

    assert len(invocations) == 1
    assert invocations[0].name == "image_gen"
    assert invocations[0].arguments == {"prompt": "hi"}


def test_missing_name_is_skipped():
    parser = FilesystemModuleUsageParser()
    content = """
    [RUN_MODULE]{"args": {"foo": "bar"}}[/RUN_MODULE]
    """
    response = CompleteResponse(content=content)

    invocations = parser.parse(response)

    assert invocations == []
