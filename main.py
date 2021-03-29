#!/usr/bin/env python3
import argparse
import csv
import logging
from pathlib import Path

import yaml

from azure_devops_connector import AzureDevopsConnector
from git_repository import GitRepository
from model.config import Configuration
from scanner import Scanner


def scan(config: Configuration, output_all: bool):
    for org_config in config.organizations:
        connector = AzureDevopsConnector(org_config.name, org_config.password)

        logging.info(f"Fetching repos from {org_config.name} organization...")
        repo_infos = list(connector.get_repos())
        logging.info("Repos fetched.")

        for repo_info in repo_infos:
            repo_config = org_config.get_project(repo_info.project).get_repository(repo_info.name)
            if repo_config.skip:
                logging.debug(f"Skipped {repo_info}.")
                continue

            logging.info(f"Processing {repo_info}...")
            try:
                scanner = Scanner(org_config, repo_config, repo_info)
                last_push = connector.get_last_push_date(repo_info.project, repo_info.id)
                new_secrets = []

                if scanner.should_scan(last_push):
                    logging.debug(f"Starting scan for {repo_info}...")
                    new_secrets = scanner.scan()
                    scanner.save()
                else:
                    logging.info(f"Skipped {repo_info} because there were no new pushes.")

                yield repo_info, scanner.get_all_secrets() if output_all else new_secrets

            except Exception as e:
                logging.exception(e)

            logging.info(f"Processed {repo_info}.")


def execute(config: Configuration, output_all: bool, output_file: str):
    with open(output_file, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["secret", "project", "repository", "file", "commit"])
        writer.writeheader()
        for repo_info, secrets in scan(config, output_all):
            for secret in secrets:
                row = {"secret": secret["line"].strip() or secret["file"],
                       "project": repo_info.project,
                       "repository": repo_info.name,
                       "file": secret["file"],
                       "commit": secret["commit"]}
                print(row)
                writer.writerow(row)


def main():
    script_directory = Path(__file__).parent
    default_config_file = "config.yaml"
    default_config_file_path = script_directory / default_config_file
    default_cache_path = Path("~/.azure-devops-secret-finder").expanduser()

    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--config', '-c', action='store', dest='config_file', default=default_config_file_path, help=f'Configuration file. Defaults to {default_config_file}')
    parser.add_argument('--cache', action='store', dest='cache_path', default=default_cache_path, help=f'Cache location. Defaults to {default_cache_path}')
    parser.add_argument('--all', '-a', action="store_true", dest='output_all', default=False, help="Also outputs the previously found results.")
    parser.add_argument('--output', '-o', action="store", dest='output_file', default="/dev/null", help="File where a CSV report will be saved. Defaults to /dev/null")
    parser.add_argument('-v', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")
    parser.add_argument('-q', action="store_true", dest='quiet', default=False, help="Sets log level to error.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("git").setLevel(logging.INFO)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    else:
        logging.getLogger().setLevel(logging.INFO)

    cache_path = Path(args.cache_path)
    Scanner.results_path = cache_path / "results"
    GitRepository.repos_path = cache_path / "repos"
    Scanner.results_path.mkdir(parents=True, exist_ok=True)
    GitRepository.repos_path.mkdir(parents=True, exist_ok=True)

    with open(args.config_file, "r") as f:
        configuration = Configuration(yaml.safe_load(f))

    execute(configuration, args.output_all, args.output_file)


if __name__ == "__main__":
    main()
