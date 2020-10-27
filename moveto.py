import requests
import re
import json
import gitlab

from requests.auth import HTTPBasicAuth
from io import StringIO
from loguru import logger


JIRA_URL = 'http://bi12gвпfdata8.ddns.net:8008/'
JIRA_ACCOUNT = ('afl1вапexan12der', '1234521trewq')
JIRA_PROJECT = 'DEV'
GITLAB_URL = 'http://150.136.4.127:8929/'
GITLAB_TOKEN = 'JhLGdfUrDRfdвпваzSoRAoinG9'
GITLAB_PROJECT = 'devsecops/devsecops'
GITLAB_PROJECT_ID = 6
VERIFY_SSL_CERTIFICATE = False

gitlab = gitlab.Gitlab(GITLAB_URL, private_token = GITLAB_TOKEN)
gitlab.auth()

# jira username: gitlab username
GITLAB_USER_NAMES = {
    'alexander': 'apodolyan',
    'olytvynenko': 'olytvynenko',
    'admin': 'ruslan',
    'yspivak': 'yspivak',
    'verbeckii': 'dmitrii',
    'bohdan': 'bohdan',
    'az': 'az',
    'imorgun': 'imorgun',
    'vzaretskiy': 'vzaretskiy',
}

jira_issues = requests.get(
    JIRA_URL + 'rest/api/2/search?jql=project=%s+&maxResults=10000' % JIRA_PROJECT,
    auth=HTTPBasicAuth(*JIRA_ACCOUNT),
    verify=VERIFY_SSL_CERTIFICATE,
    headers={'Content-Type': 'application/json'})

for issue in jira_issues.json()['issues']:  
    reporter = issue['fields']['reporter']['name']
    status = issue['fields']['status']['statusCategory']['name'] 
    team = ['alexander', 'olytvynenko', 'admin', 'yspivak', 'verbeckii', 'bohdan', 'az', 'imorgun', 'vzaretskiy']

    if reporter in team:
        try:
            user = issue['fields']['assignee']['name']
            get_user = requests.get(GITLAB_URL + 'api/v4/users?username=' + GITLAB_USER_NAMES.get(user, reporter)) 
            user_id = get_user.json()[0]['id']
        except:
            logger.error(reporter)

        gl_issue = requests.post(
            GITLAB_URL + 'api/v4/projects/%s/issues' % GITLAB_PROJECT_ID,
            headers={'PRIVATE-TOKEN': GITLAB_TOKEN,'SUDO': GITLAB_USER_NAMES.get(reporter, reporter)},
            verify=VERIFY_SSL_CERTIFICATE,
            data={
                'title': issue['fields']['summary'],
                'description': issue['fields']['description'],
                'created_at': issue['fields']['created'],
            })

        gl_issue = gl_issue.json()['iid']

        project = gitlab.projects.get(GITLAB_PROJECT_ID)
        issue_gl = project.issues.get(gl_issue)
        issue_gl.assignee_id = user_id
        issue_gl.labels = status
        issue_gl.save()

        issue_info = requests.get(
            JIRA_URL + 'rest/api/2/issue/%s/?fields=attachment,comment' % issue['id'], 
            auth=HTTPBasicAuth(*JIRA_ACCOUNT),
            verify=VERIFY_SSL_CERTIFICATE,
            headers={'Content-Type': 'application/json'}
        ).json()

        for comment in issue_info['fields']['comment']['comments']:
            author = comment['author']['name']
            body = re.sub("[\(\[].*?[\)\]]", "", comment['body'])

            note_add = requests.post(
                GITLAB_URL + 'api/v4/projects/%s/issues/%s/notes' % (GITLAB_PROJECT_ID, gl_issue),
                headers={'PRIVATE-TOKEN': GITLAB_TOKEN,'SUDO': GITLAB_USER_NAMES.get(author, author)},
                verify=VERIFY_SSL_CERTIFICATE,
                data={
                    'body': body,
                    'created_at': comment['created']
                })

        try:
            if len(issue_info['fields']['attachment']):
                for attachment in issue_info['fields']['attachment']:
                    author = attachment['author']['name']

                    _file = requests.get(
                        attachment['content'],
                        auth=HTTPBasicAuth(*JIRA_ACCOUNT),
                        verify=VERIFY_SSL_CERTIFICATE,)
                    _content = StringIO(_file.content)

                    file_info = requests.post(
                        GITLAB_URL + 'api/v4/projects/%s/uploads' % GITLAB_PROJECT_ID,
                        headers={'PRIVATE-TOKEN': GITLAB_TOKEN,'SUDO': GITLAB_USER_NAMES.get(author, author)},
                        files={
                            'file': (
                                attachment['filename'],
                                _content)
                        },
                        verify=VERIFY_SSL_CERTIFICATE)

                    del _content

                    requests.post(
                        GITLAB_URL + 'api/v4/projects/%s/issues/%s/notes' % (GITLAB_PROJECT_ID, gl_issue),
                        headers={'PRIVATE-TOKEN': GITLAB_TOKEN,'SUDO': GITLAB_USER_NAMES.get(author, author)},
                        verify=VERIFY_SSL_CERTIFICATE,
                        data={
                            'body': file_info.json()['markdown'],
                            'created_at': attachment['created']
                        })
        except:
            logger.error('Attachments not found')

        logger.info("Created issue #" + str(gl_issue)) 
    else:
        logger.error(reporter)
