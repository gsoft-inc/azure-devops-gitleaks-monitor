import logging
from pathlib import Path
from urllib.parse import quote

import git

import model.config
from model.git_repository import GitRepositoryInformation
from util import rmdir


class GitRepository(object):
    repos_path: Path = None

    def __init__(self,
                 organization_config: model.config.OrganizationConfiguration,
                 repo_config: model.config.GitRepositoryConfiguration,
                 repo_info: GitRepositoryInformation):
        self.repo: git.Repo = None
        self.path = GitRepository.repos_path / repo_info.name

        self._repo_config = repo_config
        self._repo_info = repo_info

        encoded_organization = quote(repo_info.organization)
        encoded_project = quote(repo_info.project)
        encoded_name = quote(repo_info.name)
        self._remote_url = f"https://{organization_config.username}:{organization_config.password}@dev.azure.com/{encoded_organization}/{encoded_project}/_git/{encoded_name}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.repo, "git"):
            self.repo.git.clear_cache()
        del self.repo
        if not self._repo_config.persist:
            rmdir(self.path)

    def update(self):
        if not self._repo_config.persist and self.path.exists():
            logging.warning(f"Local repository already existed for {self._repo_info}. Deleting it...")
            rmdir(self.path)

        if not self.path.exists():
            logging.debug(f"Cloning {self._repo_info} to {self.path}...")
            git.Git(str(GitRepository.repos_path)).clone(self._remote_url, self.path)
            logging.debug(f"{self._repo_info} cloned.")

        self.repo = git.Repo(str(self.path))

        logging.debug(f"Fetching updates from {self._repo_info} to {self.path}...")
        for remote in self.repo.remotes:
            remote.fetch()
        logging.debug(f"Updates fetched from {self._repo_info} to {self.path}.")

    def get_branches(self):
        return dict((b.name, b.commit.hexsha) for b in self.repo.remote().refs)

    def get_commits(self):
        return self.repo.git.rev_list("--all").split("\n")

