import os
import config
import dateutil.parser
import json
import tempfile
import logging
import toml
from git_repository import GitRepository
from model.config import OrganizationConfiguration, GitRepositoryConfiguration
from model.git_repository import GitRepositoryInformation
from datetime import datetime, timezone


class Scanner(object):
    def __init__(self, org_config: OrganizationConfiguration, repo_config: GitRepositoryConfiguration, repo_info: GitRepositoryInformation):
        self._org_config = org_config
        self._repo_config = repo_config
        self._repo_info = repo_info
        self._scan_file = config.data_path / f"{repo_info.id}.json"

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

    def scan(self):
        with GitRepository(self._org_config, self._repo_config, self._repo_info) as repo:
            repo.update()

            commits = repo.get_commits()
            self._scan["commits"] = commits

            old_commits = self._previous_scan.get("commits")

            if old_commits:
                commits_to_scan = list(set(commits) - set(old_commits))
                new_secrets = self._find_secrets(repo, commits_to_scan)
            else:
                new_secrets = self._find_secrets(repo)

            if not new_secrets:
                return []

            secrets = self._previous_scan.get("secrets", [])[:]
            secrets.extend(new_secrets)
            self._scan["secrets"] = secrets
            return new_secrets

    def get_all_secrets(self):
        return self._scan.get("secrets") or self._previous_scan.get("secrets")

    def save(self):
        j = json.dumps(self._scan, indent=1)
        with self._scan_file.open("w") as f:
            f.write(j)

    def _find_secrets(self, repo: GitRepository, commits_to_scan=None):
        commits_file = Scanner._create_commits_file(commits_to_scan)
        config_file = self._create_config_file()
        report = tempfile.mktemp()

        if commits_to_scan:
            logging.info(f"Scanning {len(commits_to_scan)} new commits for {self._repo_info}...")
        else:
            logging.info(f"Scanning whole repository for {self._repo_info}...")

        try:
            command = f'gitleaks --path="{repo.path}" --config-path=gitleaks-rules.toml -o "{report}"'
            if commits_file:
                command += f" --commits-file={commits_file}"

            if config_file:
                command += f" --additional-config={config_file}"

            logging.debug(command)

            os.system(command)
            if os.path.exists(report):
                with open(report, "r") as f:
                    return json.load(f)
            else:
                return None
        finally:
            logging.debug(f"{self._repo_info} scanned.")
            if os.path.exists(report):
                os.remove(report)
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

