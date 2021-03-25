from model.config import Configuration
from pathlib import Path
import yaml

home_path = Path("~").expanduser() # git config --system core.longpaths true
data_path = home_path / "azure-devops-secret-finder"
repos_path = data_path / "repos"

repos_path.mkdir(parents=True, exist_ok=True)


def load_configuration(config_file) -> Configuration:
    with open(config_file, "r") as f:
        return Configuration(yaml.safe_load(f))
