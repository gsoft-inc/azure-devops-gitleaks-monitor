import logging
import subprocess
from pathlib import Path

from gitleaks_exception import GitleaksException


class GitleaksExecutor:
    def __init__(self, repo_path, report_file, commits_file, config_file):
        self._repo_path = repo_path
        self._report_file = report_file
        self._commits_file = commits_file
        self._config_file = config_file

    def execute(self):
        global_config_file = "data/gitleaks-rules.toml"

        command = ["gitleaks",
                   "--path", self._repo_path,
                   "--config-path", global_config_file,
                   "-o", self._report_file]

        if self._commits_file:
            command.extend(("--commits-file", self._commits_file))

        if self._config_file:
            command.extend(("--additional-config", self._config_file))

        logging.debug(command)

        error_occurred = False
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=Path(__file__).parent) as p:
            while p.poll() is None:
                line = p.stdout.readline().strip()
                if line:
                    error_occurred |= self._handle_log(line)

            line = p.stdout.read().strip()
            if line:
                error_occurred |= self._handle_log(line)

        if error_occurred:
            raise GitleaksException(f"Gitleak did not complete successfully.")

    @staticmethod
    def _handle_log(line):
        split = line.split(" ")
        if len(split) <= 1:
            return False

        if split[1].startswith("level=info"):
            logging.info(line)
        elif split[1].startswith("level=warning"):
            logging.warning(line)
        elif split[1].startswith("level=error"):
            logging.error(line)
            return True

        return False
