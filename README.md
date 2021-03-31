# azure-devops-gitleaks-monitor

[Gitleaks](https://github.com/zricethezav/gitleaks) wrapper to monitor Azure DevOps repositories for new secrets and send the results to a Slack channel or a csv file.

If a repository has already been scanned, only new commits will be analyzed.

## Setup
Install Gitleaks
```
GO111MODULE=on go get github.com/zricethezav/gitleaks/v7
```

Install azure-devops-gitleaks-monitor
```
python3 setup.py install
```

## Usage
```
usage: azure-devops-gitleaks-monitor [-h] [--config CONFIG_FILE] [--cache CACHE_PATH] [--all] [--output OUTPUT_FILE] [-v] [-q]

Azure DevOps Gitleaks monitor

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG_FILE, -c CONFIG_FILE
                        Configuration file. Defaults to config.yaml
  --cache CACHE_PATH    Cache location. Defaults to ~/.azure-devops-secret-finder
  --all, -a             Also outputs the previously found results.
  --output OUTPUT_FILE, -o OUTPUT_FILE
                        File where a CSV report will be saved. Defaults to /dev/null
  --slack, -s           Send slack notifications to the configured webhooks when secrets are found.                      
  --lock, -l            Only allow one instance of the tool to run at the time.
  -v                    Increases output verbosity.
  -q                    Sets log level to error.
```

### Recommended usage
Generate a report with all the existing secrets.
You might need to configure custom whitelists to avoid false positives.
```
azure-devops-gitleaks-monitor --config config.xml --all --output report.csv
```

Create a cron job that executes the following command to send new secrets to Slack.
It is recommended to run the tool on all repositories at least once before to avoid sending too many messages to Slack.
```
azure-devops-gitleaks-monitor --config config.xml --lock --slack
```

## License

Copyright © 2020, GSoft inc. This code is licensed under the Apache License, Version 2.0. You may obtain a copy of this license [here](https://github.com/gsoft-inc/gsoft-license/blob/master/LICENSE).
