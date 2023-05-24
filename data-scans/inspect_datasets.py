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

# Note: before running, be sure to install google-cloud-dlp==1.0.0. 
# Don't use a more recent version of the library as project_path() has since been removed. 

from google.cloud import dlp_v2
from google.cloud import bigquery

region = 'us-central1'
inspect_project = 'sdw-conf-b1927e-bcc1'
inspect_datasets = ['crm', 'finwire', 'hr', 'oltp', 'sales']
#inspect_datasets = ['crm']

result_project = 'sdw-data-gov-b1927e-dd69'
result_datasets = ['crm_dlp', 'finwire_dlp', 'hr_dlp', 'oltp_dlp', 'sales_dlp']
#result_datasets = ['crm_dlp']

bq_client = bigquery.Client(project=inspect_project)
dlp_client = dlp_v2.DlpServiceClient()
parent = dlp_client.common_project_path(result_project)

scan_period_days = 1

def inspect():

    for index, inspect_dataset in enumerate(inspect_datasets):
        tables = bq_client.list_tables(inspect_project + '.' + inspect_dataset) 

        for table in tables:
            print("scanning {}.{}.{}".format(table.project, table.dataset_id, table.table_id))
            start_job(inspect_dataset, table.table_id, result_datasets[index])

def start_job(inspect_dataset, table, result_dataset):    

    inspect_job_data = {
        'storage_config': {
            'big_query_options': {
                'table_reference': {
                    'project_id': inspect_project,
                    'dataset_id': inspect_dataset,
                    'table_id': table
                }
            }
        },
        'inspect_config': {
            "info_types": [
              {
                "name": "CREDIT_CARD_NUMBER"
              },
              {
                "name": "EMAIL_ADDRESS"
              },
              {
                "name": "STREET_ADDRESS"
              },
              {
                "name": "PHONE_NUMBER"
              },
              {
                "name": "PERSON_NAME"
              },
              {
                "name": "FIRST_NAME"
              },
              {
                "name": "LAST_NAME"
              },
              {
                "name": "GENDER"
              },
              {
                "name": "DATE_OF_BIRTH"
              },
              {
                "name": "AGE"
              },
              {
                "name": "ETHNIC_GROUP"
              },
              {
                "name": "LOCATION_COORDINATES"
              },
              {
                "name": "IP_ADDRESS"
              }
            ],
             "min_likelihood": "LIKELY",
        },
        'actions': [
            {
                'save_findings': {
                    'output_config':{
                        'table':{
                            'project_id': result_project,
                            'dataset_id': result_dataset,
                            'table_id': table
                        }
                    }
                
                },
            },
        ]
    }

    parent = 'projects/' + result_project + '/locations/' + region

    schedule = {
        "recurrence_period_duration": {"seconds": scan_period_days * 60 * 60 * 24}
    }

    job_trigger = {
        "inspect_job": inspect_job_data,
        "display_name": table,
        "description": "CDMC inspection job",
        "triggers": [{"schedule": schedule}],
        "status": dlp_v2.JobTrigger.Status.HEALTHY,
    }

    
    response = dlp_client.create_job_trigger(
        request={"parent": parent, "job_trigger": job_trigger}
    )

    print(f"Successfully created trigger {response.name}")
    
    #response = dlp_client.create_dlp_job(parent=parent, inspect_job=inspect_job_data)
    #print(response)
    
if __name__ == '__main__':
    inspect()