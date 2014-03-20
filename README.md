AmCAT - Amsterdam Content Analysis Toolkit
==========================================

## Installation and Configuration

### Prerequisites

Most of the (python) prerequisites for AmCAT are automatically installed using pip (see below). To install the non-python requirements, you can use the following (on ubuntu):

```sh
$ sudo apt-get install unrtf rabbitmq-server python-pip python-dev libxml2-dev libxslt-dev lib32z1-dev postgresql postgresql-server-dev-9.1 postgresql-contrib-9.1
```

It is probably best to install AmCAT in a virtual environment. Run the following commands to setup and activate a virtual environment for AmCAT: (on ubuntu)

```sh
$ sudo apt-get install python-virtualenv
$ virtualenv amcat-env
$ source amcat-env/bin/activate
```

If you use a virtual environment, every time you start working with AmCAT you need to repeat the `source` line to load the environment. If you don't use a virtual environment, you will need to run most pip command below using `sudo`. 

### Database

AmCAT requires a database to store its documents in. The default settings look for a postgres database 'amcat' on localhost. To set up the current user as a superuser in postgres and create the database, use:

```sh
$ sudo -u postgres createuser -s $USER
$ createdb amcat
```

### Elastic

AmCAT uses elasticsearch for searching articles. Since we use a custom similarity to provide hit counts instead of relevance, this needs to be installed 'by hand'. You can probably skip this and rely on a pre-packaged elasticsearch if you don't care about hit counts, although you still need to install the elasticsearch plugins.

First, install oracle java (from http://www.webupd8.org/2012/01/install-oracle-java-jdk-7-in-ubuntu-via.html)

```sh
$ sudo add-apt-repository ppa:webupd8team/java
$ sudo apt-get update
$ sudo apt-get install oracle-java7-installer
```

Next, download and extract elasticsearch and our custom hitcount jar, and install the required plugins:

```sh
curl  https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.0.tar.gz | tar xvz
wget http://amcat.vu.nl/plain/hitcount.jar
elasticsearch-1.0.0/bin/plugin -install elasticsearch/elasticsearch-lang-python/1.2.0
elasticsearch-1.0.0/bin/plugin -install elasticsearch/elasticsearch-analysis-icu/1.12.0
elasticsearch-1.0.0/bin/plugin -install mobz/elasticsearch-head
```

Now you are ready to start elasticsearch. I usually start it in a secondary terminal if I am running AmCAT locally so I can directly inspect error messages, but you could also run it as a daemon:

```sh
ES_CLASSPATH=hitcount.jar elasticsearch-1.0.0/bin/elasticsearch -Des.index.similarity.default.type=nl.vu.amcat.HitCountSimilarityProvider
```

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

If you install amcat via cloning, be sure to add the new directory to the pythonpath, e.g.:

```sh
export PYTHONPATH=$PYTHONPATH:$HOME/amcat
```

### Setting up the database

Whichever way you installed AmCAT, you need tocall the syncdb command to populate the database and set the elasticsearch mapping:

```sh
python -m amcat.manage syncdb
```

### Start AmCAT web server

For debugging, it is easiest to start amcat using runserver:

```sh
python -m amcat.manage runserver
```

### Start celery worker

Finally, to use the query screen you need to start a celery worker. In a new terminal, type:

```sh
celery -A amcat.amcatcelery worker -l info -Q amcat
```

(if you are using a virtual environment, make sure to `activate` that first)

## Configuring AmCAT

The main configuration parameters for AmCAT reside in the [settings](https://github.com/amcat/amcat/tree/master/settings) folder. In many places, these settings are defaults that can be overridden with environment variables. 
