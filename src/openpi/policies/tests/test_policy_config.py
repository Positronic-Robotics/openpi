import pytest

from openpi import transforms as _transforms
from openpi.policies import policy_config as _policy_config
from openpi.training import config as _config


@pytest.mark.parametrize(
    "config_name", ["pi05_droid", "pi05_droid_jointpos", "pi05_positronic_lowmem", "pi05_libero", "pi0_aloha_sim"]
)
def test_the_example_observation_gives_the_model_every_image_it_reads(config_name: str):
    train_config = _config.get_config(config_name)
    data_config = train_config.data.create(train_config.assets_dirs, train_config.model)
    example = _policy_config.make_example_observation(train_config)
    inputs = _transforms.compose(data_config.data_transforms.inputs)(example)
    assert inputs["image"].keys() == train_config.model.fake_obs().images.keys()
