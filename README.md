# peakorc

The peak-orchestrator is the core API for peak. It interfaces with a postgresql database to store testsuite, test, and time-series data related to tests. Additionally, the `peakorc` API creates other requests to the `peakrunner` to initiate tests, and provides data for `peakweb` views.

### development setup

#### configure the database

Enable the RHSCL repo and install the `rh-postgresql95-postgresql` package:

```
# subscription-manager repos --enable rhel-server-rhscl-7-rpms
# yum install rh-postgresql95-postgresql scl-utils
```
Start the postgresql service, and initialise the database:

```
# yum install rh-postgresql95 scl-utils
# scl enable rh-postgresql95 bash
# postgresql-setup --initdb
# systemctl start rh-postgresql95-postgresql

```
Create the `peakdb` and a user:

```
# su - postgres -c 'scl enable rh-postgresql95 -- createdb peakdb'
# su - postgres -c 'scl enable rh-postgresql95 -- createuser --interactive peak --pwprompt'
```

Edit the `pg_hba.conf` file to allow the new user access to the database:

```
# cat /var/opt/rh/rh-postgresql95/lib/pgsql/data/pg_hba.conf
...
# TYPE   DATABASE     USER           ADDRESS       METHOD

# "local" is for Unix domain socket connections only
local     all          all                         peer
host      peakdb       peak          127.0.0.1/32  md5
host      all          all           127.0.0.1/32  ident
```
Grant the user access to the `peakdb`

```
# su - postgres
$ scl enable rh-postgresql95 bash
$ psql

psql (9.5.4)
Type "help" for help.

postgres=# grant all privileges on database peakdb to peak;
GRANT
```

#### configure and start peakorc

Create the database tables:

```
$ python
Python 2.7.5 (default, Aug  2 2016, 04:20:16) 
[GCC 4.8.5 20150623 (Red Hat 4.8.5-4)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> from peakmodels import *
>>> init_tables()
```

Configure environment variables for the postgresql database:

```
$ export PEAKDB_USER=peak
$ export PEAKDB_PASS=peak
$ export PEAKDB_HOST=127.0.0.1
```

Create a virtualenv and install the `peakorc` requirements:

```
$ virtualenv peakenv
$ source peakenv/bin/activate
$ pip install -r requirements.txt
```

Start the service with gunicorn:

```
gunicorn --bind 0.0.0.0:8080 peakorc:api
```
