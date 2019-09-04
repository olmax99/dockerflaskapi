# Docker Flask API [![Build Status](https://travis-ci.org//olmax99/dockerflaskapi.png)](https://travis-ci.org//olmax99/dockerflaskapi)

This is a web API project with a capability of distributed background 
workers. Its main purpose is to read larger datasets from API endpoints
and storing those into a data lake (AWS S3).

--- 

**Project Design**

![Graph](images/dockerflaskapi.png)

- Implement s3fs with rexrey docker-plugin [https://rexray.readthedocs.io/en/stable/user-guide/schedulers/docker/plug-ins/aws/#aws-s3fs](https://rexray.readthedocs.io/en/stable/user-guide/schedulers/docker/plug-ins/aws/#aws-s3fs)
- docker plugins [https://docs.docker.com/engine/extend/plugin_api/](https://docs.docker.com/engine/extend/plugin_api/)
- Create role/user for rexray, replace latest with fixed version
- Do Tutorial [https://aws.amazon.com/blogs/compute/amazon-ecs-and-docker-volume-drivers-amazon-ebs/](https://aws.amazon.com/blogs/compute/amazon-ecs-and-docker-volume-drivers-amazon-ebs/)

## Prerequisites

For local development, the following components are required on the local machine:

+ Pipenv
+ Python Version 3.6.9
+ Docker installed [official Docker docs](https://docs.docker.com/)
+ Docker-Compose
+ RexRay Docker Plugin s3fs [https://rexray.readthedocs.io/en/stable/](https://rexray.readthedocs.io/en/stable/)
+ aws-cli installed [https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)

---


**NOTE:** Currently, Celery will fail on Python 3.7 due to conflicting 
naming of packages using `async`, which is now a keyword in Python. 
Temporarily downgraded to `3.6.9` until solved.


## Quickstart

---

**NOTE:** For demonstration purposes, this project assumes the [https://github.com/olmax99/serverlessbaseapi](https://github.com/olmax99/serverlessbaseapi) 
project as the data source and to be up and running.

### 1. Preparing the project environment

In the directory  `dockerflaskapi/webflaskapi`:

```
$ pipenv install
$ pipenv shell

(webflaskapi)$ pipenv install Flask
(webflaskapi)$ pipenv install flask-restplus
(webflaskapi)$ pipenv install flask-redis
(webflaskapi)$ pipenv install sqlalchemy
(webflaskapi)$ pipenv install psycopg2
(webflaskapi)$ pipenv install pytest


```

In PyCharm:

In PyCharm > Settings > Project Interpreter:
+ Verify that the Project Interpreter `Pipenv(webflaskapi)` is selected.

*NOTE:*   PyCharm should be opened with the webflaskapi directory as the
  top folder. Otherwise the pipenv interpreter might behave in an 
  unexpected way.

In PyCharm > Tools > Python Integrated Tools > Testing

+ Set default test runner: pytest

*NOTE:*   Installing from PyCharm or even from both terminal and 
  PyCharm should make no difference. Ensure that *Pipfile.lock* is 
  up-to-date. In Pipfile directory simply run `$ pipenv lock` for 
  creating a new `Pipfile.lock`.


### 2. Create environment credentials

There are two files containing the database access credentials that 
need to be created manually.

From the terminal:

**NOTE:** All values provided here need to match the values provided in
the `.env` file.

Inside the `dockerflaskapi` directory:

```
$ vim .env.web.dev

# parameters need to match with those of .env file
REDIS_URI=redis://:super_secret2@redis.flaskapi:6379/0
CELERY_BROKER_URL=redis://:super_secret2@redis.flaskapi:6379/0
CELERY_RESULT_BACKEND=redis://:super_secret2@redis.flaskapi:6379/0
PERMITS_URL=<cfn-apigateway-public-url>                   <-- Get from 'serverless base api' project
PERMITS_KEY=<x-api-key>                                   <-- Get from 'serverless base api' project

$ vim .env.worker.dev

CELERY_BROKER_URL=redis://:super_secret2@redis.flaskapi:6379/0
CELERY_RESULT_BACKEND=redis://:super_secret2@redis.flaskapi:6379/0

$ vim .env

REDIS_PASSWD=super_secret2
REDIS_URI=redis://:super_secret2@redis.flaskapi:6379/0

```

### 3. Run the project

#### 1. Set the applications run mode

There are two ways of running the app in development mode. By default 
the `web` container will run in sleep, and flask is invoked in debug.

1. If you want to run the Flask app directly from nginx/uwsgi, comment 
out the line starting with `command: ...` in 
`dockerflaskapi/docker-compose.development.yml`:

```
# command: pipenv run flask run --host=0.0.0.0 --port=5000
# Infinite loop, to keep it alive, for debugging
# command: bash -c "while true; do echo 'sleeping...' && sleep 10; done"  <-- COMMENT OUT

```

2. If you want to run the application in DEBUG mode for developing on the
code base, uncomment the last line. It is then recommended to run docker 
in detached mode

#### 2. Build and run the docker image in development

```
$ docker-compose -f docker-compose.development.yml up -d --build

```

#### 3. Run the web application

**NOTE:** Skip this step if Flask is running directly from nginx/uwsgi

---

Only in DEBUG mode, in directory `dockerflaskapi` run the following command:

```
$ docker-compose -f docker-compose.development.yml exec web.flaskapi sh -c 'pipenv run flask run --host=0.0.0.0 --port=5000'

# OPTIONALLY - view real-time worker logs
$ docker logs -f dockerflaskapi_worker.flaskapi_1

```

---

1. The Swagger Api documentation can be accessed in your browser at `localhost:80`.
2. Flower can be accessed on `localhost:5555`

### 4. Create a development table in AWS Athena

```
$ aws cloudformation validate-template --template-body file://cloudformation.development.glue.yaml

$ aws cloudformation create-stack --stack-name dev-flaskapi-01 file://cloudformation.development.glue.yaml

```


### 5. Delete resources

```
$ aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE
$ aws cloudformation delete-stack --stack-name dev-flaskapi-01

```


## Running the tests

TravisCI is preconfigured to run automated tests on:

- PRs related to merges into master or any branch named `ci-<name>`
- `git push` changes into master or any branch named `ci-<name>`

For manually running the tests:

### Run pytest

In directory `dockerflaskapi`:

```
$ docker-compose -f docker-compose.testing.yml up -d --build

$ docker-compose -f docker-compose.testing.yml exec web.testing sh -c 'pytest -v --disable-warnings'

$ docker-compose -f docker-compose.testing.yml exec worker.testing sh -c 'pytest -v --disable-warnings'

$ docker-compose -f docker-compose.testing.yml down


```


## General Instructions

### Changing The Project Name

One of the first tasks when adjusting the business logic for repurposing this project is to
the change following files:

```
# In uwsgi.ini replace the following line:

# module = flaskapi.api
module = <your project>.api


# In docker-compose.development.yml
environment:
  # - FLASK_APP=flaskapi/api.py
  - FLASK_APP=<your project>/api.py

#In .travis.yml change the environment variables:
env:
  # - APP_DIR="$TRAVIS_BUILD_DIR/webflaskapi"
  - APP_DIR="$TRAVIS_BUILD_DIR/<your project>"

# Rename the parent directory
$ cp -r webflaskapi <your project>
$ rm -r webflaskapi

```

*NOTE*: It is recommended to use PyCharm for the refactoring of the project
directories, since all import statements need to be changed along the way.

### Changing Nginx Configurations

The flask docker is based on a project from *Sebastián Ramírez* [uwsgi-nginx-flask-docker](https://github.com/tiangolo/uwsgi-nginx-flask-docker). 

A few adjustments have been made along the way, but all configuration and
general instruction references are holding for this project, too.

### Install RexRay s3fs Docker Plugin

- Debian Buster
- Linux 4.19.0-5-amd64 #1 SMP Debian 4.19.37-5+deb10u2 (2019-08-08) x86_64 GNU/Linux

#### 1. Install RexRay binaries manually

[https://rexray.readthedocs.io/en/latest/user-guide/installation/](https://rexray.readthedocs.io/en/latest/user-guide/installation/)

```
$ curl -sSL https://rexray.io/install | sh -s -- stable

# verify that the client is installed
$ rexray --help

# verify that Rexrayay volume is connected  <-- NOTE: AT THIS POINT THIS WILL FAIL!!
# Use the DEBUG function in order to identify the global target directory for the config.yml
$ rexray volume ls -l debug

# expected
# /home/user/.rexray/etc/config.yml

```

#### 2. Create RexRay client config.yml

Conduct [https://rexray.readthedocs.io/en/stable/user-guide/servers/libstorage/](https://rexray.readthedocs.io/en/stable/user-guide/servers/libstorage/) for more advanced
libstorage configurations.


**NOTE**: THIS IS THE CLIENT SIDE CONFIG IN `/home/user/.rexray/etc/config.yml`!!

Use a webform at  [https://rexrayconfig.cfapps.io/](https://rexrayconfig.cfapps.io/)
or create manually:

```
rexray:
  logLevel: info
libstorage:
  logging:
    level: info
  service: s3fs
  integration:
    volume:
      operations:
        create:
          default:
            size: 1
s3fs:
  accessKey: ***
  secretKey: ***
  # region: <your region> DO NOT MESS WITH REGION FOR THE MOMENT

```

```
# Verify that volume is connected to account
$ rexray volume ls -l debug

# You should see all s3 buckets listet in your target account


```

#### 3. Install RexRay plugin

- Ensure that the RexRay serverside driver modul is running
- YOU NEED TO HAVE A FILE IN `/etc/rexray/config.yml` (Note this is NOT the client side config file!!)

```
$ sudo service rexray status
# active (running)
# In case it is not active
$ sudo systemctl start rexray

docker plugin install rexray/s3fs:0.11.4 \
  S3FS_ACCESSKEY=*** \
  S3FS_SECRETKEY=*** 
  
# Verify install
$ docker plugin ls

# ID                  NAME                 DESCRIPTION                                     ENABLED
# 5ii5t3e34n8i        rexray/s3fs:0.11.4   REX-Ray FUSE Driver for Amazon Simple Storag…   true

```

**NOTE:** Without the keys you will get a `rexray.sock error`.

#### 4. Run a docker with s3fs volume driver

```
# All permanent rexray connected buckets will now be displaed as docker volumes
$ docker volume ls

# Create a bucket, and docker rexray volume
$ docker volume create --driver rexray/s3fs:0.11.4 --name test-rexray-local-6281

# Confirm action
$ docker volume ls
$ docker volume inspect test-rexray-local-6281
$ docker run -ti -v test-rexray-local-6281:/data nginx:latest mount | grep "/data"

```
# Expected
s3fs on /data type fuse.s3fs (rw,nosuid,nodev,relatime,user_id=0,group_id=0)

```

# or enter bucket
$ docker run -ti -v test-rexray-local-6281:/data nginx:latest

```

---

**NOTE**:
1. Always use `/data` in docker volume, since this is default config for rexray
2. Bucket will be PUBLIC by default - CHANGE IF NECESSARY!!

#### 5. Delete test bucket

```
$ docker volume rm test-rexray-local-6281

```

---

**NOTE:** At this point in time tmy custom region is not picked up, but instead always
`US East (N. Virginia)`. For basic functionality it is not of concern.


## Author

**OlafMarangone** - *Initial work* - [Gitlab](https://github.com/olmax99/dockerflaskapi.git)  
contact: olmax99@gmail.com

## License

MIT
 
Copyright (C) 2019 Olaf Marangone  

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:  
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.  
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS 
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
