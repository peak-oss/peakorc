import falcon
from peakorc.peakmodels import *
from playhouse.shortcuts import model_to_dict
import json
import math
import uuid
import requests
import kubernetes.client
import kubernetes.config
from kubernetes.client.apis import batch_v1_api
import os

class PeakSuiteResource():
    def on_get(self, req, resp, suite_uuid):
        try:
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            resp.body = json.dumps(model_to_dict(suite),
                                   indent=4,
                                   sort_keys=True,
                                   default=str)
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404

class PeakJobsResource():
    def on_get(self,req, resp, suite_uuid):
        try:
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            resp.body = json.dumps({'jobs':[model_to_dict(job) for job in suite.jobs]},
                                    indent=4,
                                    default=str)
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404

class StopPeakSuiteJobs():
    def __init__(self, k8sclient):
        self.k8sclient = k8sclient

    def on_post(self, req, resp, suite_uuid):
        try: 
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            body = kubernetes.client.V1DeleteOptions(propagation_policy="Background")
            for job in suite.jobs:
                name = job.job_name
                self.k8sclient.delete_namespaced_job(name=name, body=body, namespace=os.environ['OPENSHIFT_BUILD_NAMESPACE'])
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404

class PeakSuitesResource():
    def __init__(self, k8sclient):
        self.k8sclient = k8sclient

    def on_get(self, req, resp):
        # check if this is a paginated query
        paginate = False
        page_by = 10
        page = 0
        to_json = {}
        for k,v in req.params.items():
            if k == "page":
                paginate = True
                page = int(v)
        suites = PeakTestSuite.select().order_by(PeakTestSuite.initiated.desc())
        if paginate:
            # count the total suites before paginating the query
            to_json['total_pages'] = int(math.ceil(float(suites.count())/float(page_by)))
            suites = suites.paginate(page,page_by)
        to_json['suites'] = [model_to_dict(s) for s in suites]
        resp.body = json.dumps(to_json, indent=4, default=str)

    def on_post(self, req, resp):
        requests_per_node = int(req.get_header('node-requests'))
        url = req.get_header('test-url')
        description = req.get_header('description')
        nodes = int(req.get_header('nodes'))
        total_requests = requests_per_node * nodes
        suite_uuid = uuid.uuid4()
        suite = PeakTestSuite.create(uuid=suite_uuid, requests=total_requests,
                                     description=description)
        # use the kubernetes API to create batched jobs
        # kubernetes requires that each job has a unique 
        # name
        for i in range(0,nodes):
            job_manifest = {
                    'kind': 'Job',
                    'spec': {
                        'template':
                        {'spec':
                            {'containers': [
                                {'image':os.environ['PEAKTEST_IMG'],
                                    'name': 'peaktest',
                                 'env': [
                                     { 'name': 'REQUESTS',
                                       'value': str(requests_per_node)
                                     },
                                     { 'name': 'URL',
                                       'value': url
                                     },
                                     { 'name': 'UUID',
                                       'value': str(suite_uuid)
                                     },
                                     { 'name': 'INFLUX_URL',
                                       'value': os.environ['INFLUX_URL']
                                     },
                                     {
                                       'name': 'POD_NAMESPACE',
                                       'valueFrom': {
                                         'fieldRef': {
                                           'fieldPath': 'metadata.name'
                                         }
                                       }
                                     }
                                 ],
                                 }],
                                 'restartPolicy': 'Never'},
                            'metadata': {'name': 'peaktest'}}},
                        'apiVersion': 'batch/v1',
                        'metadata': {'name': 'peaktest'+str(suite_uuid)[:8]+str(i)}}
            job = self.k8sclient.create_namespaced_job(body=job_manifest, namespace=os.environ['POD_NAMESPACE'])
            PeakTestJob.create(job_name=job.metadata.name, suite=suite)

        resp.body = json.dumps({'id': str(suite_uuid) })


api = falcon.API(middleware=[PeeweeConnectionMiddleware()])

kubernetes.config.load_incluster_config()
batch_client = batch_v1_api.BatchV1Api()

peak_suite = PeakSuiteResource()
peak_suites = PeakSuitesResource(batch_client)
peak_jobs = PeakJobsResource()
stop_suite = StopPeakSuiteJobs(batch_client)

api.add_route('/suites/', peak_suites)
api.add_route('/suites/{suite_uuid}', peak_suite)
api.add_route('/suites/{suite_uuid}/jobs', peak_jobs)
api.add_route('/suites/{suite_uuid}/stop', stop_suite)

