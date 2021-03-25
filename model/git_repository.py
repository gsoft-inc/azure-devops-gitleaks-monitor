class GitRepositoryInformation:
    def __init__(self, organization, project, name, id, remote_url):
        self.organization = organization
        self.project = project
        self.name = name
        self.id = id
        self.remote_url = remote_url

    def __str__(self):
        return f"{self.organization}/{self.project}/{self.name}"
