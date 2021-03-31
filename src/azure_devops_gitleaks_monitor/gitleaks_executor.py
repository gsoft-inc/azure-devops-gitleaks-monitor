import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Dict, Any

from gitleaks_exception import GitleaksException


class GitleaksExecutor:
    def __init__(self, repo_path, commits_file, config_file):
        self._repo_path = repo_path
        self._commits_file = commits_file
        self._config_file = config_file

    def execute(self) -> Iterable[Dict[str, Any]]:
        report_file = tempfile.mktemp()
        try:
            self._execute_internal(report_file)
            if not os.path.exists(report_file):
                raise GitleaksException("Gitleaks did not complete successfully.")
            with open(report_file, "r") as f:
                return json.load(f) or []
        finally:
            if os.path.exists(report_file):
                os.remove(report_file)

    def _execute_internal(self, report_file):
        global_config_file = Path(__file__).parent / "data/gitleaks-rules.toml"

        command = ["gitleaks",
                   "--path", self._repo_path,
                   "--config-path", global_config_file,
                   "-o", report_file]

        if self._commits_file:
            command.extend(("--commits-file", self._commits_file))

        if self._config_file:
            command.extend(("--additional-config", self._config_file))

        command = self._fix_paths(command)

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
            raise GitleaksException("Gitleaks did not complete successfully.")

    @staticmethod
    def _handle_log(line):
        line = line.strip()
        split = line.split(" level=", 1)
        if len(split) <= 1:
            return False

        if split[1].startswith("info"):
            logging.info(line)
        elif split[1].startswith("warning"):
            logging.warning(line)
        elif split[1].startswith("error"):
            logging.error(line)
            return True

        return False

    @staticmethod
    def _fix_paths(command):
        new_command = []
        for part in command:
            if isinstance(part, Path):
                part = str(part)
                if os.name == "nt":
                    # Workaround for https://github.com/zricethezav/gitleaks/issues/532
                    part = part.replace("\\", "/")

            new_command.append(part)
        return new_command
