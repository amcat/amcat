AmCAT - Amsterdam Content Analysis Toolkit
==========================================

Master: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=master)](https://travis-ci.org/amcat/amcat) Release 3.4: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=release-3.3)](https://travis-ci.org/amcat/amcat)

*Note:* the following instructions are for the unstable development version. 
To install stable releases, please see the readme file for those releases:

[Installation instructions for 3.4 (stable)](https://github.com/amcat/amcat/blob/release-3.4/README.md)


## Installation and Configuration

### Prerequisites

Most of the (python) prerequisites for AmCAT are automatically installed using pip (see below). To install the non-python requirements, you can use the following (on Ubuntu 15.10 or 16.04):

```sh
sudo apt-get install antiword unrtf rabbitmq-server python-pip postgresql postgresql-contrib python-virtualenv git postgresql-server-dev-9.4 python-dev libxml2-dev libxslt-dev
```

If you want to compile lxml and psycopg2 yourself (through pip), you need to install:

```sh
sudo apt-get build-dep python-psycopg2 python-lxml
```

You can avoid compiling libraries by installing some dependencies through apt:

```sh
sudo apt-get install python-lxml python-amqplib python-psycopg2 python-requests python-pygments
```

It is probably best to install AmCAT in a virtual environment. Run the following commands to setup and activate a virtual environment for AmCAT: (on ubuntu)

```sh
virtualenv amcat-env
source amcat-env/bin/activate
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
wget https://download.elasticsearch.org/elasticsearch/release/org/elasticsearch/distribution/deb/elasticsearch/2.1.1/elasticsearch-2.1.1.deb
sudo dpkg -i elasticsearch-2.1.1.deb
rm elasticsearch-2.1.1.deb

# Install plugins
cd /usr/share/elasticsearch
sudo bin/plugin install mobz/elasticsearch-head
sudo bin/plugin install analysis-icu
sudo bin/plugin install amcat/hitcount

# Enable hitcount as default similarity provider, and enable groovy scripting
cat <<EOT | sudo tee --append /etc/elasticsearch/elasticsearch.yml
index.similarity.default.type: hitcountsimilarity
script.inline: on
script.update: on
EOT

# Restart elastic
sudo systemctl stop elasticsearch
sudo systemctl start elasticsearch
```

**Warning**: We enabled a non-sandboxed scripting language (Groovy). Make sure to restrict access to the elastic instance by untrusted parties, as this allows executing arbitrary code as the user `elasticsearch`.

### Installing AmCAT (pip install from git)

Now you are ready to install AmCAT. The easiest way to do this is to `pip install` it direct from github. 
This is not advised unless you use a virtual environment.

```sh
pip install git+https://github.com/amcat/amcat.git
```

### Installing AmCAT (clone)

Alternatively, clone the project from github and pip install the requirements. If you plan to make changes to 
AmCAT, this is probably the best thing to do. 

```sh
git clone https://github.com/amcat/amcat.git
pip install -r amcat/requirements.txt
```

If you install amcat via cloning, be sure to add the new directory to the pythonpath. 
Also, add AMCAT_ES_LEGACY hash to the environment.
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
