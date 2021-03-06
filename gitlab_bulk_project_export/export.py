import cgi
import json
import os
import time
from os import path

import click
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


@click.command()
@click.option(
    '-i', '--gitlab-instance',
    help='Base URL of the GitLab Server you want to export projects from '
          + '(e.g.: https://gitlab.com).',
    prompt=True,
    envvar='GBPE_GITLAB_INSTANCE')
@click.option(
    '-t', '--access-token',
    help='Access Token (API) for access to the GitLab API.',
    prompt=True,
    envvar='GBPE_GITLAB_ACCESS_TOKEN',
    show_envvar=True,
    hide_input=True)
@click.option(
    '-o', '--output-dir',
    help='Directory where to put the exported projects into (relative or absolute path).',
    prompt=True,
    envvar='GBPE_OUTPUT_DIR')
@click.option(
    '--dry-run', is_flag=True,
    help='Only show projects that would be exported, neither schedule or donwnload exports.',
    default=False, show_default=True)
def export(gitlab_instance, access_token, output_dir, dry_run):
    gitlab_api_url = f'{gitlab_instance}/api/v4'
    retry_strategy = Retry(
        total=10,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['HEAD', 'GET', 'OPTIONS', 'POST'],
        backoff_factor=3
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    http.headers.update({'Authorization': f'Bearer {access_token}'})

    click.echo('Fetching projects to export...')
    projects_to_export = []
    page = 0
    done = False
    while not done:
        page += 1
        response = http.get(f'{gitlab_api_url}/projects', params={'page': page, 'membership': 1})
        projects = json.loads(response.content)

        for project in projects:
            projects_to_export.append({
                'id': project['id'],
                'name': project['name'],
                'path': project['path'],
                'path_namespaced': project['path_with_namespace'],
            })

        done = response.headers.get('X-Page') == response.headers.get('X-Total-Pages')

    click.echo(f'Trying to exporting the following ({len(projects_to_export)}) projects:')
    for project in projects_to_export:
        click.echo(f'{project["id"]}: {project["path_namespaced"]}')

    if dry_run:
        click.echo('Dry Run: Quit! Nothing was exported.')
        return

    scheduled_projects = []
    failed_scheduled_projects = []
    with click.progressbar(projects_to_export,
                           label='Trying to schedule exports for projects',
                           length=len(projects_to_export)) as bar:
        for project in bar:
            export_request = http.post(f'{gitlab_api_url}/projects/{project["id"]}/export')
            if export_request.status_code != 202:
                reason = json.loads(export_request.content)
                project.update({'reason': reason['message']})
                failed_scheduled_projects.append(project)
            else:
                scheduled_projects.append(project)
    if len(failed_scheduled_projects) > 0:
        click.echo('WARNING: Export for following projects could not be scheduled:')
        for project in failed_scheduled_projects:
            click.echo(f'{project["name"]} ({project["id"]}): {project["reason"]}')

    output_dir = path.join(path.abspath(output_dir),
                           f'gitlab-export-{time.strftime("%Y-%m-%d-%H-%M-%S")}')
    finished_ids = []
    iteration = 1
    with click.progressbar(length=len(scheduled_projects),
                           label='Waiting for projects to be exported and download') as bar:
        while len(finished_ids) != len(scheduled_projects):
            for project in scheduled_projects:
                if project['id'] in finished_ids:
                    continue

                export_status = http.get(f'{gitlab_api_url}/projects/{project["id"]}/export')
                status = json.loads(export_status.content)
                if status['export_status'] != 'finished':
                    continue

                download = http.get(f'{gitlab_api_url}/projects/{project["id"]}/export/download')
                filename = f'{project["path"]}_{project["id"]}.tar.gz'
                if 'Content-Disposition' in download.headers:
                    _, cd_params = cgi.parse_header(download.headers.get('Content-Disposition'))
                    filename = cd_params['filename']
                namespace = project['path_namespaced']
                project_export_dir = path.join(output_dir, namespace)
                os.makedirs(project_export_dir)

                with open(path.join(project_export_dir, filename), 'wb') as f:
                    f.write(download.content)

                finished_ids.append(project['id'])
                bar.update(len(finished_ids))

            time.sleep(iteration * 3)
            iteration += 1

    click.echo(f'Exported {len(finished_ids)} projects!')
