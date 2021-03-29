from datetime import datetime
from typing import Dict, Iterator

import dateutil.parser
import pytz
import requests
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from requests.auth import HTTPBasicAuth

from model.git_repository import GitRepositoryInformation


class AzureDevopsConnector(object):
    def __init__(self, organisation, password):
        self._organization_url = f'https://dev.azure.com/{organisation}'

        self._requests_auth = HTTPBasicAuth('', password)
        credentials = BasicAuthentication('', password)
        connection = Connection(base_url=self._organization_url, creds=credentials)

        self._organisation = organisation
        self._core_client = connection.clients.get_core_client()
        self._git_client = connection.clients.get_git_client()

    def get_repos(self) -> Iterator[GitRepositoryInformation]:
        for project in self._get_projects():
            for repo in self._get_repositories(project.name):
                yield GitRepositoryInformation(self._organisation, project.name, repo.name, repo.id, repo.remote_url)

    def get_last_push_date(self, project_name, repository_id) -> datetime:
        response = requests.get(
            f"{self._organization_url}/{project_name}/_apis/git/repositories/{repository_id}/pushes?api-version=6.0&$top=1",
            auth=self._requests_auth)
        if response.status_code == 200:
            j = response.json()
            value = j.get("value")
            if value and len(value) == 1:
                return dateutil.parser.parse(value[0]["date"])
        return datetime.min.replace(tzinfo=pytz.UTC)

    def get_branches(self, repository_id) -> Dict[str, str]:
        return dict(("origin/" + branch.name, branch.commit.commit_id) for branch in self._git_client.get_branches(repository_id))

    def _get_projects(self):
        response = self._core_client.get_projects()
        while response is not None:
            for project in response.value:
                yield project
            if response.continuation_token is not None and response.continuation_token != "":
                response = self._core_client.get_projects(continuation_token=response.continuation_token)
            else:
                break

    def _get_repositories(self, project_name):
        return self._git_client.get_repositories(project_name)
