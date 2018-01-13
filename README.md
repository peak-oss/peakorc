# peakorc

The peak-orchestrator is the core API for peak. It interfaces with a postgresql database to store testsuite, test, and time-series data related to tests. Additionally, the `peakorc` API creates other requests to the `peakrunner` to initiate tests, and provides data for `peakweb` views.

### development setup

Enable the RHSCL repo and install the `rh-postgresql95-postgresql` package.

```
$ sudo subscription-manager repos --enable rhel-server-rhscl-7-rpms
$ sudo yum install rh-postgresql95-postgresql
```

Start the postgresql service, and initialise the database.

Configure environment variables for the postgresql database:

```
$ export PEAKDB_USER=peak
$ export PEAKDB_PASS=peak
$ export PEAKDB_HOST=127.0.0.1
```
