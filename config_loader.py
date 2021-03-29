import os
import re

import yaml

from model.config import Configuration

path_matcher = re.compile(r'.*\$\{([^}^{]+)\}.*')


def path_constructor(loader, node):
    return os.path.expandvars(node.value)


class EnvVarLoader(yaml.SafeLoader):
    pass


EnvVarLoader.add_implicit_resolver('!path', path_matcher, None)
EnvVarLoader.add_constructor('!path', path_constructor)


def load_configuration(config_file) -> Configuration:
    with open(config_file, "r") as f:
        return Configuration(yaml.load(f, Loader=EnvVarLoader))
