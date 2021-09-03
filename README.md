# GitLab Bulk Project Export
Python Tool for Bulk Exports of Projects within a GitLab instance.


## Installation and Usage
```shell
# Install
pip install git+https://github.com/marvinweber/gitlab-bulk-project-export.git

# Execute
gitlab-bulk-project-export --help
```

Exports are limited to projects the use is a member of. Otherwise scheduling and
downloading of exports would not even be possible.

## Rate Limit
GitLab has a (default) rate limit for project export schedules of 6 per minute.
As an administrator, you can increase the limit in the admin control section.  
More about the rate limit: https://docs.gitlab.com/ee/user/admin_area/settings/import_export_rate_limits.html

## E-Mail Spam
By default, GitLab will send you an e-mail for every exported project that is
ready to be downloaded. To avoid a lot of e-mail spam, you can disable your
notifications for the export (temporarily).
