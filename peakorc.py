import falcon
from peakmodels import *
from playhouse.shortcuts import model_to_dict
import json
import uuid
import requests

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


class PeakNewSuiteResource():
    def on_post(self, req, resp):
        requests_per_node = int(req.get_header('node-requests'))
        url = req.get_header('test-url')
        description = req.get_header('description')
        nodes = int(req.get_header('nodes'))
        total_requests = requests_per_node * nodes
        suite_uuid = uuid.uuid4()
        status_uri = 'http://172.17.0.1:8080'
        suite = PeakTestSuite.create(uuid=suite_uuid, requests=total_requests,
                                     description=description)
        for i in range(0, nodes):
            test_uuid = uuid.uuid4()
            PeakTest.create(url=url, requests_req=requests_per_node,
                          uuid=test_uuid, suite=suite)
            # TODO: Instead of creating a request directly to peakrunner, add
            # a message to the queue and have a worker pull it off and create
            # the request.
            # This will provide far better UI response times.
            docker_req = requests.post("http://localhost:6511/start",
                                 headers={'requests': str(requests_per_node),
                                          'test-url': url,
                                          'uuid': str(test_uuid),
                                          'status-uri': status_uri})
        resp.body = json.dumps({'id': str(suite_uuid) })


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
            num_ok = 0
            num_error = 0
            data = (PeakTimeData
                     .select()
                     .where(PeakTimeData.suite == suite)
                     .order_by(PeakTimeData.duration))
            for entry in data:
                num_ok += entry.num_ok
                num_error += entry.num_error
                timedata.append((entry.duration, num_ok, num_error))

            resp.body = json.dumps(timedata)
        except PeakTestSuite.DoesNotExist:
            resp.status = falcon.HTTP_404

class PeakSuitesResource():
    def on_get(self, req, resp):
        suites = PeakTestSuite.select()
        resp.body = json.dumps([model_to_dict(s) for s in suites],
                               indent=4,
                               default=str)

class PeakSuitesTestsDetailResource():
    def on_get(self, req, resp, suite_uuid):
        suite = PeakTestSuite.get(PeakTestSuite.uuid == suite_uuid)
        tests = PeakTest.select().where(PeakTest.suite == suite)
        resp.body = json.dumps([model_to_dict(t) for t in tests],
                                indent=4,
                                default=str)

api = falcon.API(middleware=[PeeweeConnectionMiddleware()])

peak_suite_new = PeakNewSuiteResource()
peak_status = PeakStatusResource()
peak_suite_time = PeakSuiteTimeDataResource()
peak_suites = PeakSuitesResource()
peak_suite = PeakSuiteResource()
peak_test = PeakTestResource()
peak_suite_tests = PeakSuitesTestsDetailResource()

api.add_route('/test_suite/new', peak_suite_new)
api.add_route('/suites/', peak_suites)
api.add_route('/suites/{suite_uuid}', peak_suite)
api.add_route('/suites/{suite_uuid}/tests', peak_suite_tests)
api.add_route('/status/{test_uuid}', peak_status)
api.add_route('/time_data/{suite_uuid}', peak_suite_time)
api.add_route('/test/{test_uuid}', peak_test)
