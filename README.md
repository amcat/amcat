AmCAT - Amsterdam Content Analysis Toolkit
==========================================

Master: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=master)](https://travis-ci.org/amcat/amcat) Release 3.4: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=release-3.3)](https://travis-ci.org/amcat/amcat)

## Experimental Docker Support

We've created a Dockerfile and docker-compose.yml file that should allow you to automatically run AmCAT and all dependencies with Docker. See [amcat/amcat-docker](http://github.com/amcat/amcat-docker)


## Installation instructions for 3.4 (stable)

The installation instructions for AmCAT 3.4 (the last stable release) can be found 
[here](https://github.com/amcat/amcat/blob/release-3.4/README.md)


## Installation and Configuration for development version

The following instructions are for the (unstable) development version. 
To install stable releases, please use the link above.


### Prerequisites

Most of the (python) prerequisites for AmCAT are automatically installed using pip (see below). To install the non-python requirements, you can use the following (on Ubuntu 15.10 or 16.04):

```sh
sudo apt-get install antiword unrtf rabbitmq-server python3-pip postgresql postgresql-contrib python3-venv git postgresql-server-dev-9.5 python3-dev libxml2-dev libxslt-dev graphviz pspp redis-server r-base python3-lxml python3-amqplib python3-psycopg2 python3-requests python3-pygments docker.io
```


### Installing AmCAT 

Clone the project from github and pip install the requirements. 
We usually create a virtual environment within the amcat folder, but of course you can change the location if you wish:

```sh
git clone https://github.com/amcat/amcat.git
cd amcat
pyvenv env
env/bin/pip install wheel -r amcat/requirements.txt
```

### Elastic

AmCAT uses elasticsearch for searching articles. The easiest way to install elastic is through docker:

```sh
docker run --name elastic -dp 9200:9200 amcat/amcat-elastic-docker:5.4.3
```

Note: depending on your system settings, you might have to run docker with `sudo docker ...`

Note 2: This is fine for testing/developing, but *absolutely not suitable for production* use! For production, install elastic normally, preferably on more than 1 node, or see https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html for more information on installing elastic through docker on production systems. 

For configuring elastic for AmCAT, see the [Dockerfile](https://github.com/amcat/amcat-elastic-docker/blob/master/Dockerfile)

### Setting up the database

Whichever way you installed AmCAT, you need to call the migrate command to populate the database and set the elasticsearch mapping:

```sh
sudo -u postgres createuser -s $USER
createdb amcat
env/bin/python -m amcat.manage migrate
```

You can create a superuser by running:

```sh
env/bin/python -m amcat.manage createsuperuser
```

### Collecting static files

AmCAT uses [bower](http://bower.io/) to install javascript/CSS libraries. On Ubuntu, you need to install the legacy version of `nodejs` first, and then install bower by using `npm`:

```sh
sudo apt-get install nodejs-legacy npm
sudo npm install -g bower
```

Then, in the top-directory of AmCAT itself run:

```sh
bower install
```


### Start AmCAT web server

For debugging, it is easiest to start amcat using runserver:

```sh
env/bin/python -m amcat.manage runserver
```

### Start celery worker

Finally, to use the query screen you need to start a celery worker. In a new terminal, type:

```sh
env/bin/python -m amcat.manage celery worker -l info -Q amcat
```

(if you are using a virtual environment, make sure to `activate` that first)

## Configuring AmCAT

The main configuration parameters for AmCAT reside in the [settings](https://github.com/amcat/amcat/tree/master/settings) folder. In many places, these settings are defaults that can be overridden with environment variables. 
