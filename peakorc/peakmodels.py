from peewee import *
import datetime
import os

psql_db = PostgresqlDatabase(
    'peakdb',
    user=os.environ['PEAKDB_USER'],
    password=os.environ['PEAKDB_PASS'],
    host=os.environ['PEAKDB_HOST'])


class PeeweeConnectionMiddleware(object):
    def process_request(self, req, resp):
        psql_db.connect(reuse_if_open=True)


class BaseModel(Model):
    class Meta:
        database = psql_db


class PeakTestSuite(BaseModel):
    initiated = DateTimeField(default=datetime.datetime.now)
    uuid = UUIDField()
    description = TextField(default="not_specified")
    requests = BigIntegerField(default=0)

psql_db.create_tables([PeakTestSuite], safe=True)
