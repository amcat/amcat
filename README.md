AmCAT - Amsterdam Content Analysis Toolkit
==========================================

Master: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=master)](https://travis-ci.org/amcat/amcat)

Release 3.4: [![Build Status](https://travis-ci.org/amcat/amcat.png?branch=release-3.4)](https://travis-ci.org/amcat/amcat)


## Installation and Configuration for release 3.4 (stable)

AmCAT 3.4 is the current stable (release) build of AmCAT. It is targeted at ubuntu 14.04, elastic 1.4.4, python 2.7, django 1.8. 

### Prerequisites

Most of the (python) prerequisites for AmCAT are automatically installed using pip (see below). To install the non-python requirements, you can use the following (on ubuntu):

Note: these requirements are for ubuntu 14.04 LTS (trusty). If you use a different distro or version, you may need to adapt these instructions, e.g. a different postgresql server and R repository. 

```sh
$ sudo apt-get install antiword unrtf rabbitmq-server python-pip python-dev libxml2-dev libxslt-dev lib32z1-dev postgresql postgresql-server-dev-9.3 postgresql-contrib-9.3 python-virtualenv git graphviz
```

It is probably best to install AmCAT in a virtual environment. Run the following commands to setup and activate a virtual environment for AmCAT: (on ubuntu)

```sh
$ virtualenv amcat-env
$ source amcat-env/bin/activate
```

If you use a virtual environment, every time you start working with AmCAT you need to repeat the `source` line to load the environment. If you don't use a virtual environment, you will need to run most pip command below using `sudo`. 

### Install R

AmCAT uses R to directly supply .rda files. 
The R version in the ubuntu repository is quite old, so we need to add a cran mirror to the apt sources:

```sh
sudo sh -c "echo 'deb https://cran.rstudio.com/bin/linux/ubuntu trusty/' > /etc/apt/sources.list.d/r-cran-trusty.list"
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E084DAB9
sudo apt-get update
sudo apt-get install r-base-dev
```

### Database

AmCAT requires a database to store its documents in. The default settings look for a postgres database 'amcat' on localhost. To set up the current user as a superuser in postgres and create the database, use:

```sh
$ sudo -u postgres createuser -s $USER
$ createdb amcat
```

### Elastic

AmCAT uses elasticsearch for searching articles. Since we use a custom similarity to provide hit counts instead of relevance, this needs to be installed 'by hand'. You can probably skip this and rely on a pre-packaged elasticsearch if you don't care about hit counts, although you still need to install the elasticsearch plugins.

First, install oracle java: 
```sh
$ sudo add-apt-repository ppa:webupd8team/java
$ sudo apt-get update
$ sudo apt-get install oracle-java8-installer 
```


Next, download and extract elasticsearch and our custom hitcount jar, and install the required plugins:

```sh
# Download and install elasticsearch
wget "https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.4.deb"
sudo dpkg -i elasticsearch-1.4.4.deb
rm elasticsearch-1.4.4.deb

# Install plugins
sudo /usr/share/elasticsearch/bin/plugin -install elasticsearch/elasticsearch-analysis-icu/2.4.2
sudo /usr/share/elasticsearch/bin/plugin -install mobz/elasticsearch-head
sudo /usr/share/elasticsearch/bin/plugin -install lukas-vlcek/bigdesk


# Allow dynamic scripting 
echo -e "\nscript.disable_dynamic: false" | sudo tee -a /etc/elasticsearch/elasticsearch.yml

# Install hitcount.jar (this has been converted to a proper plugin in 3.5)
sudo wget http://hmbastiaan.nl/martijn/amcat/hitcount.jar -O /usr/share/elasticsearch/hitcount.jar
sudo editor /etc/init.d/elasticsearch

# Add after ES_HOME:
ES_CLASSPATH=$ES_HOME/hitcount.jar
export ES_CLASSPATH

# Add to DAEMON_OPTS:
-Des.index.similarity.default.type=nl.vu.amcat.HitCountSimilarityProvider

# Save file and close editor
# Restart elasticsearch
sudo service elasticsearch restart
```


**Warning**: By default, elasticsearch listens on all interfaces (port 9200) and does not have authentication enabled. Please make sure to configure elasticsearch and/or your firewall to block unauthorized accesss. 

### Installing AmCAT (clone)

Clone the project from github and pip install the requirements. 

```sh
git clone -b release-3.4 https://github.com/amcat/amcat.git
pip install -r amcat/requirements.txt
```

Be sure to add the new directory to the pythonpath and add AMCAT_ES_LEGACY hash to the environment, e.g. using the lines below.
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

On older ubuntu versions, if the above does not work, try installing nodejs via Chris Lea's ppa:

```sh
sudo add-apt-repository ppa:chris-lea/node.js
sudo apt-get update
sudo apt-get install nodejs
sudo apt-get upgrade nodejs
sudo npm install -g bower
```

Then, in the top-directory of AmCAT itself run:

```sh
bower install
```

### Setting up the database

You need to call the syncdb command to populate the database and set the elasticsearch mapping:

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
DJANGO_SETTINGS_MODULE=settings celery -A amcat.amcatcelery worker -l info -Q amcat
```

(if you are using a virtual environment, make sure to `activate` that first)

## Configuring AmCAT

The main configuration parameters for AmCAT reside in the [settings](https://github.com/amcat/amcat/tree/master/settings) folder. In many places, these settings are defaults that can be overridden with environment variables. 
