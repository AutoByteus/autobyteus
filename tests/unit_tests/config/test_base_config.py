from autobyteus.configs.base_config import BaseConfig
import pytest


# @pytest.mark.skip(reason="Skip until the test is fixed")
def test_load_llm_configs():
    # Initialize the config with an empty model_config_path
    config = BaseConfig()

    print(config.get_all())

    assert isinstance(config.get_all(), dict)  # Check if the config is a dictionary
    assert (
        "OPENAI_API_KEY" in config.get_all().keys()
    )  # Check if the key is in the config
    assert "MODEL" in config.get_all().keys()  # Check if the key is in the config


@pytest.mark.skip(reason="Skip until the test is fixed")
def test_load_llm_configs_wrong_path():
    # Initialize the config with a wrong model_config_path

    config = BaseConfig(model_config_path="wrong_path")
    assert isinstance(config.get_all(), dict)  # Check if the config is a dictionary
    # assert isinstance(config.get_all(), dict)  ## inital keys
