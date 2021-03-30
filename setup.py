from setuptools import setup, find_packages

setup(
    name='azure_devops_gitleaks_monitor',
    version='0.0.1',
    description='Gitleaks wrapper to monitor Azure DevOps repositories for new secrets and send the results to a Slack channel or a csv file.',
    url='https://github.com/gsoft-inc/azure-devops-gitleaks-monitor',
    author='Mathieu Gascon-Lefebvre',
    author_email='mathieuglefebvre@gmail.com',
    license='Apache',
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={'azure_devops_gitleaks_monitor': ['data/*']},
    install_requires=[
        'azure-devops',
        'GitPython',
        'python-dateutil',
        'pytz',
        'pyyaml',
        'requests',
        'toml',
        'pid',
        'slack-sdk',
    ],
    entry_points={
        'console_scripts': ['azure-devops-gitleaks-monitor = azure_devops_gitleaks_monitor.main:main'],
    },
)
