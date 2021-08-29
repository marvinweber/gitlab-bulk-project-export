from setuptools import setup, find_packages

setup(
    name='gitlab_bulk_project_export',
    version='0.2.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'gitlab-bulk-project-export = gitlab_bulk_project_export.export:export',
        ],
    },
)
