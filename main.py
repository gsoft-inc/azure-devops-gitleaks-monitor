#!/usr/bin/env python3
import argparse
import csv
import logging
from contextlib import nullcontext
from pathlib import Path
from typing import Dict, Iterable, Any, Tuple, List

from pid import PidFile
from slack_sdk.errors import SlackRequestError

from azure_devops_connector import AzureDevopsConnector
from config_loader import load_configuration
from git_repository import GitRepository
from model.config import Configuration, GitRepositoryConfiguration
from model.git_repository_information import GitRepositoryInformation
from scanner import Scanner
from slack_message_builder import SlackMessageBuilder
from slack_sdk.webhook import WebhookClient


def scan(config: Configuration, output_all: bool) -> Iterable[Tuple[GitRepositoryInformation, GitRepositoryConfiguration, List[Dict[str, Any]]]]:
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

                yield repo_info, repo_config, scanner.get_all_secrets() if output_all else new_secrets

            except Exception as e:
                logging.exception(e)

            logging.info(f"Processed {repo_info}.")


def execute(config: Configuration, output_all: bool, output_file: str, output_slack: bool):
    with open(output_file, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["secret", "project", "repository", "file", "commit"])
        writer.writeheader()
        for repo_info, repo_config, secrets in scan(config, output_all):
            for secret in secrets:
                row = {"secret": secret["line"].strip() or secret["file"],
                       "project": repo_info.project,
                       "repository": repo_info.name,
                       "file": secret["file"],
                       "commit": secret["commit"]}
                print(row)
                writer.writerow(row)

            if output_slack and repo_config.slack_webhook:
                webhook = WebhookClient(repo_config.slack_webhook)
                for blocks in SlackMessageBuilder(repo_info, secrets).build():
                    print({"blocks": list(blocks)})
                    response = webhook.send(text="fallback", blocks=blocks)
                    if response.status_code != 200:
                        raise SlackRequestError(f"Error when sending message blocks to slack: {response.body}")



def main():
    script_directory = Path(__file__).parent
    default_config_file = "config.yaml"
    default_config_file_path = script_directory / default_config_file
    default_cache_path = Path("~/.azure-devops-secret-finder").expanduser()

    parser = argparse.ArgumentParser(description='Azure DevOps Gitleaks monitor')
    parser.add_argument('--config', '-c', action='store', dest='config_file', default=default_config_file_path, help=f'Configuration file. Defaults to {default_config_file}')
    parser.add_argument('--cache', action='store', dest='cache_path', default=default_cache_path, help=f'Cache location. Defaults to {default_cache_path}')
    parser.add_argument('--all', '-a', action="store_true", dest='output_all', default=False, help="Also outputs the previously found results.")
    parser.add_argument('--output', '-o', action="store", dest='output_file', default="/dev/null", help="File where a CSV report will be saved. Defaults to /dev/null")
    parser.add_argument('--slack', '-s', action="store_true", dest='output_slack', default=False, help="Send slack notifications to the configured webhooks when secrets are found.")
    parser.add_argument('--lock', '-l', action="store_true", dest='lock', default=False, help="Only allow one instance of the tool to run at the time.")
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

    configuration = load_configuration(args.config_file)

    with PidFile('foo') if args.lock else nullcontext():
        execute(configuration, args.output_all, args.output_file, args.output_slack)


if __name__ == "__main__":
    main()
