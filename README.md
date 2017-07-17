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
sudo apt-get install antiword unrtf rabbitmq-server python3-pip postgresql postgresql-contrib python3-venv git postgresql-server-dev-9.5 python3-dev libxml2-dev libxslt-dev graphviz pspp redis-server r-base
```

If you want to compile lxml and psycopg2 yourself (through pip), you need to install:

```sh
sudo apt-get build-dep python3-psycopg2 python3-lxml
```

You can avoid compiling libraries by installing some dependencies through apt:

```sh
sudo apt-get install python3-lxml python3-amqplib python3-psycopg2 python3-requests python3-pygments
```

It is probably best to install AmCAT in a virtual environment. Run the following commands to setup and activate a virtual environment for AmCAT: (on ubuntu)

```sh
pyvenv env
source env/bin/activate
```

If you use a virtual environment, every time you start working with AmCAT you need to repeat the `source` line to load the environment. If you don't use a virtual environment, you will need to run most pip command below using `sudo`. 

### Database

AmCAT requires a database to store its documents in. The default settings look for a postgres database 'amcat' on localhost. To set up the current user as a superuser in postgres and create the database, use:

```sh
sudo -u postgres createuser -s $USER
createdb amcat
```

### Elastic

AmCAT uses elasticsearch for searching articles. Elasticsearch is provided as a debian package, but it does need some extra plugins to be ready for AmCAT.

```sh
wget -O /tmp/elasticsearch-5.4.0.deb https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.4.0.deb
sudo dpkg -i /tmp/elasticsearch-5.4.0.deb
rm /tmp/elasticsearch-5.4.0.deb

# Install plugins
cd /usr/share/elasticsearch
sudo bin/elasticsearch-plugin install analysis-icu
sudo bin/elasticsearch-plugin install https://github.com/amcat/hitcount/releases/download/5.4.0/hitcount-5.4.0-plugin.zip

# Install scripts (scripts can also be found in config/elasticsearch
sudo wget -q https://raw.githubusercontent.com/amcat/amcat/master/config/elasticsearch/amcat_remove_from_set.groovy -O /etc/elasticsearch/scripts/amcat_remove_from_set.groovy
sudo wget -q https://raw.githubusercontent.com/amcat/amcat/master/config/elasticsearch/amcat_add_to_set.groovy -O /etc/elasticsearch/scripts/amcat_add_to_set.groovy
sudo wget -q https://raw.githubusercontent.com/amcat/amcat/master/config/elasticsearch/amcat_lead.groovy -O /etc/elasticsearch/scripts/amcat_lead.groovy

# Restart elastic
sudo systemctl stop elasticsearch
sudo systemctl start elasticsearch
```

**Warning**: By default, elasticsearch listens on all interfaces (port 9200) and does not have authentication enabled. Please make sure to configure elasticsearch and/or your firewall to block unauthorized accesss. 

**Warning**: We enabled a non-sandboxed scripting language (Groovy). Make sure to restrict access to the elastic instance by untrusted parties, as this allows executing arbitrary code as the user `elasticsearch`.


### Installing AmCAT 

Clone the project from github and pip install the requirements. 

```sh
git clone https://github.com/amcat/amcat.git
pip install wheel
pip install -r amcat/requirements.txt
```

Be sure to add the new directory to the pythonpath and add AMCAT_ES_LEGACY hash to the environment.
If you add these lines to amcat-env/bin/activate they will be automatically set when you activate.

```sh
export PYTHONPATH=$PYTHONPATH:$HOME/amcat
export AMCAT_ES_LEGACY_HASH=N
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

### Setting up the database

Whichever way you installed AmCAT, you need to call the migrate command to populate the database and set the elasticsearch mapping:

```sh
python -m amcat.manage migrate
```

You can create a superuser by running:

```sh
python -m amcat.manage createsuperuser
```

### Start AmCAT web server

For debugging, it is easiest to start amcat using runserver:

```sh
python -m amcat.manage runserver
```

### Start celery worker

Finally, to use the query screen you need to start a celery worker. In a new terminal, type:

```sh
DJANGO_SETTINGS_MODULE=settings celery -A amcat.amcatcelery worker -l info -Q amcat
```

(if you are using a virtual environment, make sure to `activate` that first)

## Configuring AmCAT

The main configuration parameters for AmCAT reside in the [settings](https://github.com/amcat/amcat/tree/master/settings) folder. In many places, these settings are defaults that can be overridden with environment variables. 
