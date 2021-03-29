import copy
from typing import Dict, List

DEFAULT_KEY = "default"


class GitRepositoryConfiguration:
    def __init__(self, name):
        self.name = name
        self.skip = False
        self.persist = False
        self.allowlist: Dict[str, List] = {}

    def configure(self, config: Dict):
        self.skip = config.get("skip", False)
        self.persist = config.get("persist", False)

        for allowlist_type, values in config.get("allowlist", {}).items():
            self.allowlist.setdefault(allowlist_type, []).extend(values)


class GitProjectConfiguration:
    def __init__(self, name):
        self.repositories: Dict[str, GitRepositoryConfiguration] = {}
        self._default_repository_configuration = GitRepositoryConfiguration(DEFAULT_KEY)
        self.name = name

    def configure(self, config: Dict):
        repo_configs = config.get("repos", {})
        default_repo_config = repo_configs.get(DEFAULT_KEY)
        if default_repo_config:
            self._default_repository_configuration.configure(default_repo_config)

        for repo_name, repo_config in repo_configs.items():
            if repo_name != DEFAULT_KEY:
                self.get_repository(repo_name).configure(repo_config)

    def get_repository(self, repository_name):
        repository = self.repositories.get(repository_name)
        if not repository:
            repository = copy.deepcopy(self._default_repository_configuration)
            repository.name = repository_name
            self.repositories[repository_name] = repository
        return repository


class OrganizationConfiguration:
    def __init__(self, name):
        self._projects: Dict[str, GitProjectConfiguration] = {}
        self._default_project_configuration = GitProjectConfiguration(DEFAULT_KEY)
        self.name = name
        self.username = ""
        self.password = ""

    def configure(self, config: dict):
        username = config.get("username")
        if username:
            self.username = username

        password = config.get("password")
        if password:
            self.password = password

        project_configs = config.get("projects", {})
        default_project_config = project_configs.get(DEFAULT_KEY)
        if default_project_config:
            self._default_project_configuration.configure(default_project_config)

        for project_name, project_config in project_configs.items():
            if project_name != DEFAULT_KEY:
                self.get_project(project_name).configure(project_config)

    def get_project(self, project_name):
        project = self._projects.get(project_name)
        if not project:
            project = copy.deepcopy(self._default_project_configuration)
            project.name = project_name
            self._projects[project_name] = project
        return project


class Configuration:
    def __init__(self, config):
        self.organizations: list[OrganizationConfiguration] = []
        default_organization = OrganizationConfiguration(DEFAULT_KEY)

        organization_configs = config.get("organizations", {})
        default_organization_config = organization_configs.get(DEFAULT_KEY)
        if default_organization_config:
            default_organization.configure(default_organization_config)

        for organization_name, organization_config in organization_configs.items():
            if organization_name != DEFAULT_KEY:
                organization = copy.deepcopy(default_organization)
                organization.name = organization_name
                organization.configure(organization_config)
                self.organizations.append(organization)