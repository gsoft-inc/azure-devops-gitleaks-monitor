import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Iterable

import dateutil.parser
import toml

from git_repository import GitRepository
from gitleaks_executor import GitleaksExecutor
from model import OrganizationConfiguration, GitRepositoryConfiguration, GitRepositoryInformation


class Scanner(object):
    results_path: Path = None

    def __init__(self, org_config: OrganizationConfiguration, repo_config: GitRepositoryConfiguration, repo_info: GitRepositoryInformation):
        self._org_config = org_config
        self._repo_config = repo_config
        self._repo_info = repo_info
        self._scan_file = Scanner.results_path / f"{repo_info.id}.json"

        self._previous_scan = self._load_previous_scan() or {}
        self._scan = {
            "date": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "repo_id": repo_info.id,
            "project_name": repo_info.project,
            "repo_name": repo_info.name,
            "remote_url": repo_info.remote_url
        }

    def should_scan(self, last_push: datetime):
        last_scan_date = self._previous_scan.get("date")
        if not last_scan_date:
            return True

        return last_push > dateutil.parser.isoparse(last_scan_date)

    def scan(self) -> Iterable[Dict[str, Any]]:
        with GitRepository(self._org_config, self._repo_config, self._repo_info) as repo:
            repo.update()

            commits = repo.get_commits()
            self._scan["secrets"] = self._previous_scan.get("secrets", [])[:]
            self._scan["commits"] = commits

            old_commits = self._previous_scan.get("commits")

            if old_commits:
                commits_to_scan = list(set(commits) - set(old_commits))
                new_secrets = self._find_secrets(repo, commits_to_scan)
            else:
                new_secrets = self._find_secrets(repo)

            self._scan["secrets"].extend(new_secrets)
            return new_secrets

    def get_all_secrets(self) -> Iterable[Dict[str, Any]]:
        return self._scan.get("secrets") or self._previous_scan.get("secrets") or []

    def save(self):
        j = json.dumps(self._scan, indent=1)
        with self._scan_file.open("w") as f:
            f.write(j)

    def _find_secrets(self, repo: GitRepository, commits_to_scan=None) -> Iterable[Dict[str, Any]]:
        commits_file = Scanner._create_commits_file(commits_to_scan)
        config_file = self._create_config_file()

        try:
            if commits_to_scan is None:
                logging.info(f"Scanning whole repository for {self._repo_info}...")
            elif len(commits_to_scan) == 0:
                logging.info(f"No new commits for {self._repo_info}. Skipping ...")
                return []
            else:
                logging.info(f"Scanning {len(commits_to_scan)} new commits for {self._repo_info}...")

            return GitleaksExecutor(repo.path, commits_file, config_file).execute()
        finally:
            logging.debug(f"{self._repo_info} scanned.")
            if commits_file:
                os.remove(commits_file)
            if config_file:
                os.remove(config_file)

    def _load_previous_scan(self):
        if not self._scan_file.exists():
            return None

        with self._scan_file.open("r") as f:
            return json.load(f)

    def _create_config_file(self):
        allowlist = {}

        regexes = self._repo_config.allowlist.get("regexes")
        if regexes:
            allowlist["regexes"] = regexes

        paths = self._repo_config.allowlist.get("paths")
        if paths:
            allowlist["paths"] = paths

        files = self._repo_config.allowlist.get("files")
        if files:
            allowlist["files"] = files

        if len(allowlist) == 0:
            return None

        config_file = tempfile.mktemp()
        with open(config_file, "w") as f:
            toml.dump({"allowlist": allowlist}, f)

        return config_file

    @staticmethod
    def _create_commits_file(commits_to_scan):
        if not commits_to_scan:
            return None

        commits_file = tempfile.mktemp()
        with open(commits_file, "w") as f:
            f.write("\n".join(commits_to_scan))
        return commits_file

