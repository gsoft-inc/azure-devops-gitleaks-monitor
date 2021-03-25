#!/usr/bin/env python3
from azure_devops_connector import AzureDevopsConnector
from config import load_configuration
from scanner import Scanner
import logging


def main():
    logging.basicConfig(level=logging.DEBUG)

    config = load_configuration("config.yaml")
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

                if scanner.should_scan(last_push):
                    logging.debug(f"Starting scan for {repo_info}...")
                    new_secrets = scanner.scan()
                    output_secrets(new_secrets)
                    scanner.save()
                else:
                    logging.info(f"Skipped {repo_info} because there were no new pushes.")
            except Exception as e:
                logging.exception(e)

            logging.info(f"Processed {repo_info}.")


def output_secrets(secrets):
    if not secrets:
        return

    d = {}
    for secret in secrets:
        value = secret["line"].strip()
        if not value:
            value = secret["file"]
        d.setdefault(value, []).append(secret["commit"])

    for item in d.items():
        print(item)


if __name__ == "__main__":
    main()
