# Copyright 2023 Google, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account
from google.cloud import bigquery
from google.protobuf.timestamp_pb2 import Timestamp

import requests
import json
import os
import datetime
import subprocess as sp

# Read the config from the env variables
PROJECT_ID_GOV = os.getenv('PROJECT_ID_GOV')
PROJECT_ID = os.getenv('PROJECT_ID')
PROJECT_NUMBER = os.getenv('PROJECT_NUMBER')
REGION = os.getenv('REGION')
GCS_BUCKET_TPCDI = os.getenv('GCS_BUCKET_TPCDI')

# Use Application Default Credentials to avoid downloading SA Keys
SA_KEY = f"{os.path.expanduser('~')}/.config/gcloud/application_default_credentials.json"
# Tested with us-central1
DL_API = f'https://{REGION}-datalineage.googleapis.com/v1'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


class LineageManager:
    project_number = None
    storage_region = None
    process_name = None
    origin_name = None
    job_id = None
    start_time = None
    end_time = None
    source = None
    target = None

    def __init__(self,
                 project_number,
                 storage_region,
                 process_name,
                 origin_name,
                 job_id,
                 start_time,
                 end_time,
                 source,
                 target):
        self.project_number = project_number
        self.storage_region = storage_region
        self.process_name = process_name
        self.origin_name = origin_name
        self.job_id = job_id
        self.start_time = start_time
        self.end_time = end_time
        self.source = source
        self.target = target

    def create_lineage(self):

        print('create_lineage for', self.source, '->', self.target)

        process = self._create_process()

        if process == None:
            print('Error: create_process failed.')
        else:
            print('process:', process)
            run = self._create_run(process)
            print('run:', run)

            if run == None:
                print('Error: create_run failed.')
            else:
                event = self._create_event(run)
                print('event:', event)

                if event == None:
                    print('Error: create_event failed.')

    def retrieve_lineage(self):

        self._get_links_by_source(self.source)
        self._get_links_by_target(self.target)

    ######## Internal methods ########

    def _get_credentials(self):
        # credentials = service_account.Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
        # auth_req = google.auth.transport.requests.Request()
        # credentials.refresh(auth_req)
        #
        # return credentials.token

        # Get the token for the ADC to avoid downloading a SA key
        return sp.getoutput('gcloud auth application-default print-access-token')

    def _create_process(self):

        url = '{0}/projects/{1}/locations/{2}/processes'.format(
            DL_API, self.project_number, self.storage_region)
        # headers = {'Authorization' : 'Bearer ' + self._get_credentials()}
        # Get the token for the ADC
        token = sp.getoutput(
            'gcloud auth application-default print-access-token')
        headers = {'Authorization': 'Bearer ' + token}
        payload = {'displayName': self.process_name, 'origin': {
            'sourceType': 'CUSTOM', 'name': 'data_ingestion/' + self.origin_name}}
        res = requests.post(url, headers=headers,
                            data=json.dumps(payload)).json()

        if 'name' in res:
            process = res['name']
        else:
            process = None

        return process

    def _create_run(self, process):

        url = '{0}/{1}/runs'.format(DL_API, process)
        headers = {'Authorization': 'Bearer ' + self._get_credentials()}

        if self.job_id:
            payload = {'displayName': self.job_id, 'startTime': self.start_time,
                       'endTime': self.end_time, 'state': 'COMPLETED'}
        else:
            payload = {'displayName': 'Manual', 'startTime': self.start_time,
                       'endTime': self.end_time, 'state': 'COMPLETED'}

        res = requests.post(url, headers=headers,
                            data=json.dumps(payload)).json()

        if 'name' in res:
            run = res['name']
        else:
            run = None

        return run

    def _create_event(self, run):

        url = '{0}/{1}/lineageEvents'.format(DL_API, run)
        headers = {'Authorization': 'Bearer ' + self._get_credentials()}

        payload = {'links': [{'source': {'fullyQualifiedName': self.source}, 'target': {
            'fullyQualifiedName': self.target}}], 'startTime': self.start_time}
        print(payload)

        res = requests.post(url, headers=headers,
                            data=json.dumps(payload)).json()

        if 'name' in res:
            event = res['name']
        else:
            event = None

        return event

    def _get_links_by_source(self, source):

        url = '{0}/projects/{1}/locations/{2}:searchLinks'.format(
            DL_API, self.project_number, self.storage_region)
        headers = {'Authorization': 'Bearer ' + self._get_credentials()}
        payload = {'source': {'fully_qualified_name': source,
                              'location': self.storage_region}}

        res = requests.post(url, headers=headers,
                            data=json.dumps(payload)).json()
        # print(res)

        if 'links' in res:
            links = res['links']

            for link in links:
                print('Source:', source, '-> Target:',
                      link['target']['fullyQualifiedName'])
                self._get_links_by_source(link['target']['fullyQualifiedName'])
        else:
            return

    def _get_links_by_target(self, target):

        url = '{0}/projects/{1}/locations/{2}:searchLinks'.format(
            DL_API, self.project_number, self.storage_region)
        headers = {'Authorization': 'Bearer ' + self._get_credentials()}
        payload = {'target': {'fully_qualified_name': target,
                              'location': self.storage_region}}

        res = requests.post(url, headers=headers,
                            data=json.dumps(payload)).json()
        # print(res)

        if 'links' in res:
            links = res['links']

            for link in links:
                print('Target:', target, '<- Source:',
                      link['source']['fullyQualifiedName'])
                self._get_links_by_target(link['source']['fullyQualifiedName'])
        else:
            return


if __name__ == '__main__':
    project_number = PROJECT_NUMBER  # project number for solution-workspace project
    storage_region = REGION
    process_name = 'LineageManagerTest'
    origin_name = 'Origin'
    job_id = 'LineageManagerTest'
    start_time = datetime.datetime.now().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    end_time = datetime.datetime.now().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    source = 'https://www.tpc.org/'
    target = f'gs://{project_number}tpcdi-data/staging/crm/AddAcct.csv'
    lm = LineageManager(project_number,
                        storage_region,
                        process_name,
                        origin_name,
                        job_id,
                        start_time,
                        end_time,
                        source,
                        target)
    lm.create_lineage()
