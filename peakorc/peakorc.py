import falcon
from peakorc.peakmodels import *
from playhouse.shortcuts import model_to_dict
import numpy
import json
import math
import uuid
import requests
import kubernetes.client
import kubernetes.config
from kubernetes.client.apis import batch_v1_api
import os

class PeakTestResource():
    def on_get(self, req, resp, test_uuid):
        try:
            test = PeakTest.get(PeakTest.uuid == test_uuid)
            resp.body = json.dumps(model_to_dict(test),
                                   indent=4,
                                   sort_keys=True,
                                   default=str)
        except PeakTest.DoesNotExist:
            resp.status = falcon.HTTP_404


class PeakSuiteResource():
    def on_get(self, req, resp, suite_uuid):
        try:
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            resp.body = json.dumps(model_to_dict(suite),
                                   indent=4,
                                   sort_keys=True,
                                   default=str)
        except PeakTest.DoesNotExist:
            resp.status = falcon.HTTP_404


class PeakStatusResource():
    def on_post(self, req, resp, test_uuid):
        try:
            test = PeakTest.get(PeakTest.uuid == test_uuid)
            suite = test.suite
            completed = int(req.get_header('complete'))
            ok = int(req.get_header('ok'))
            duration = float(req.get_header('duration'))
            time_uuid = uuid.uuid4()
            error = completed - ok
            PeakTimeData.create(test=test, suite=suite, uuid=time_uuid,
                                requests_com = completed,
                                num_ok = ok, num_error = error,
                                duration = duration)
            #test.num_ok = ok
            # TODO: check if the number of completed matches the requested, and
            # set the boolean flag
            #test.save()
        except PeakTest.DoesNotExist:
            resp.status = falcon.HTTP_404

class PeakSuiteTimeDataResource():
    def on_get(self, req, resp, suite_uuid):
        try:
            timedata = list()
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            data = (PeakTimeData
                     .select()
                     .where(PeakTimeData.suite == suite)
                     .order_by(PeakTimeData.duration))
            for entry in data:
                timedata.append((entry.duration, entry.num_ok, entry.num_error))

            resp.body = json.dumps(timedata)
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404

class PeakSuiteAvgTimeResource():
    def on_get(self, req, resp, suite_uuid):
        try:
            # store the time-difference data for each test in the suite
            test_lists = list()
            suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
            tests = PeakTest.select().where(PeakTest.suite == suite)
            for test in tests:
                data = (PeakTimeData
                         .select()
                         .where(PeakTimeData.test == test)
                         .order_by(PeakTimeData.duration))
                test_data = list()
                prev_entry = None
                for entry in data:
                    if prev_entry:
                        test_data.append(entry.duration - prev_entry.duration)
                    prev_entry = entry
                test_lists.append(test_data)

            # now that we have lists for each test, we can average the duration
            # for each data point
            arr = numpy.array(test_lists)
            avg_data = numpy.mean(arr, axis=0)

            # iterate over each averaged duration, and calculate the
            # average response time
            timedata = list()
            tsum = 0
            for dp in avg_data:
                # peaktest returns 100 requests each time it posts back to peakorc
                avg = float(dp)/100.0
                tsum += dp

                # convert average to milliseconds
                timedata.append((tsum, 1000*avg))

            resp.body = json.dumps(timedata)
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404


class PeakSuitesResource():
    def __init__(self, status_uri, k8sclient):
        self.status_uri = status_uri
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
            test_uuid = uuid.uuid4()
            PeakTest.create(url=url, requests_req=requests_per_node,
                    uuid=test_uuid, suite=suite)
            job_manifest = {
                    'kind': 'Job',
                    'spec': {
                        'template':
                        {'spec':
                            {'containers': [
                                {'image':'docker.io/peakapi/peaktest:latest',
                                    'name': 'peaktest',
                                 'env': [
                                     { 'name': 'REQUESTS',
                                       'value': str(requests_per_node)
                                     },
                                     { 'name': 'URL',
                                       'value': url
                                     },
                                     { 'name': 'UUID',
                                       'value': str(test_uuid)
                                     },
                                     { 'name': 'STATUS_URI',
                                       'value': status_uri
                                     }
                                 ],
                                 }],
                                 'restartPolicy': 'Never'},
                            'metadata': {'name': 'peaktest'}}},
                        'apiVersion': 'batch/v1',
                        'metadata': {'name': 'peaktest'+str(test_uuid)[:8]}}
            self.k8sclient.create_namespaced_job(body=job_manifest, namespace='myproject')

        resp.body = json.dumps({'id': str(suite_uuid) })


class PeakSuitesTestsDetailResource():
    def on_get(self, req, resp, suite_uuid):
        suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
        tests = PeakTest.select().where(PeakTest.suite == suite)
        resp.body = json.dumps([model_to_dict(t) for t in tests],
                                indent=4,
                                default=str)


api = falcon.API(middleware=[PeeweeConnectionMiddleware()])

kubernetes.config.load_incluster_config()
batch_client = batch_v1_api.BatchV1Api()

status_uri = os.environ['STATUS_URI']

peak_suite = PeakSuiteResource()
peak_suites = PeakSuitesResource(status_uri, batch_client)
peak_suite_avg = PeakSuiteAvgTimeResource()
peak_suite_tests = PeakSuitesTestsDetailResource()
peak_suite_time = PeakSuiteTimeDataResource()

peak_test = PeakTestResource()
peak_test_status = PeakStatusResource()

# suites
api.add_route('/suites/', peak_suites)
api.add_route('/suites/{suite_uuid}', peak_suite)
api.add_route('/suites/{suite_uuid}/tests', peak_suite_tests)
api.add_route('/suites/{suite_uuid}/metrics/raw_response_counts', peak_suite_time)
api.add_route('/suites/{suite_uuid}/metrics/avg_response_times', peak_suite_avg)

# tests
api.add_route('/tests/{test_uuid}', peak_test)
api.add_route('/tests/{test_uuid}/status', peak_test_status)
