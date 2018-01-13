from peewee import *
import datetime
import os

psql_db = PostgresqlDatabase(
    'peakdb',
    user=os.environ['PEAKDB_USER'],
    password=os.environ['PEAKDB_PASS'],
    host=os.environ['PEAKDB_HOST'])


def init_tables():
    psql_db.create_tables([PeakTest,PeakTestSuite,PeakTimeData], safe=True)


class PeeweeConnectionMiddleware(object):
    def process_request(self, req, resp):
        psql_db.get_conn()


class BaseModel(Model):
    class Meta:
        database = psql_db


class PeakTestSuite(BaseModel):
    uuid = UUIDField()
    description = TextField(default="not_specified")
    requests = BigIntegerField(default=0)


class PeakTest(BaseModel):
    suite = ForeignKeyField(PeakTestSuite)
    uuid = UUIDField()
    requests_req = BigIntegerField(default=0)
    url = TextField()
    num_ok = IntegerField(default=0)
    time_start = DateTimeField(default=datetime.datetime.now)

class PeakTimeData(BaseModel):
    test = ForeignKeyField(PeakTest)
    suite = ForeignKeyField(PeakTestSuite)
    uuid = UUIDField()
    requests_com = BigIntegerField(default=0)
    num_ok = IntegerField(default=0)
    num_error = IntegerField(default=0)
    duration = DoubleField(default=0.0)
