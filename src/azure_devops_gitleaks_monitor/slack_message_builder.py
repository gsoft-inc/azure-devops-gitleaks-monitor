import itertools
from urllib.parse import urlencode
from typing import List, Dict, Any

from model import GitRepositoryInformation


class SlackMessageBuilder:
    bullet_emoji = ":black_small_square:"
    warning_emoji = ":warning:"
    max_line_length = 400
    max_blocks = 50

    def __init__(self, repo: GitRepositoryInformation, secrets: List[Dict[str, Any]]):
        self._repo = repo
        self._secrets = secrets

    def build(self):
        if len(self._secrets) == 0:
            return

        for blocks in itertools.zip_longest(*[iter(self._build_blocks())] * SlackMessageBuilder.max_blocks):
            yield [block for block in blocks if block]

    def _build_blocks(self):
        yield self._build_header_block()

        for commit, commit_secrets in itertools.groupby(self._secrets, lambda s: s["commit"]):
            yield self._build_commit_block(commit)

            for secret in commit_secrets:
                yield self._build_secret_block(secret)

            yield self._build_divider_block()

    def _build_repo_url(self):
        return f"https://dev.azure.com/{self._repo.organization}/{self._repo.project}/_git/{self._repo.name}"

    def _build_header_block(self):
        return {"type": "header", "text": {
            "type": "plain_text",
            "text": f"{SlackMessageBuilder.warning_emoji} New secrets found for {self._repo} {SlackMessageBuilder.warning_emoji}"
        }}

    def _build_commit_block(self, commit: str):
        commit_url = f"{self._build_repo_url()}/commit/{commit}"
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{commit_url}|{commit}>"
            }
        }

    def _build_secret_block(self, secret: Dict[str, Any]):
        query_string = urlencode({
            "version": "GC" + secret["commit"],
            "path": secret["file"],
            "line": secret["lineNumber"],
            "lineEnd": secret["lineNumber"] + 1,
            "lineStartColumn": 0,
            "lineEndColumn": 0,
        })

        file_url = f"{self._build_repo_url()}?{query_string}"
        line = secret["line"].strip() or secret["file"]
        if len(line) > SlackMessageBuilder.max_line_length:
            line = line[:SlackMessageBuilder.max_line_length] + "..."

        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{SlackMessageBuilder.bullet_emoji} <{file_url}|{secret['file']}>"
                },
                {
                    "type": "plain_text",
                    "text": line
                }
            ]
        }

    def _build_divider_block(self):
        return {"type": "divider"}

