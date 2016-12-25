#!/bin/bash -xv
###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

# This scripts installs AmCAT systemwide. It will setup:
#
# * A new user
# * AmCAT (+scrapers)
# * elasticsearch
# * postgres
# * nginx
# * letsencrypt

set -euo pipefail
IFS=$'\n\t'

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

BRANCH=master
INSTALL_DIR=/usr/local/share/amcat/
AMCAT_CELERY_QUEUE=amcat
ELASTIC_VERSION=2.3.4
ELASTIC_URL="https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/deb/elasticsearch/${ELASTIC_VERSION}/elasticsearch-${ELASTIC_VERSION}.deb"
ELASTIC_URL="https://hmbastiaan.nl/martijn/downloads/elasticsearch-${ELASTIC_VERSION}.deb"

#read -p "Server address [${HOSTNAME}]:" hostname
hostname=${hostname:-${HOSTNAME}}

uninstall(){
    systemctl stop amcat || true
    systemctl stop amcat_worker || true

    if id amcat >/dev/null 2>&1; then
      deluser amcat
    fi

    systemctl disable amcat amcat_worker || true
    rm -f /lib/systemd/system/amcat*.service
    rm -f /etc/nginx/sites-enabled/amcat /etc/nginx/sites-available/amcat
    rm -rf ${INSTALL_DIR}

    if [ -d "/usr/share/elasticsearch/bin/plugin" ]; then
        start=$(pwd)
        cd /usr/share/elasticsearch
        bin/plugin remove analysis-icu
        bin/plugin remove head
        bin/plugin remove hitcount
        cd ${start}
    fi

    dpkg --remove elasticsearch
}

purge(){
    systemctl stop amcat || true
    systemctl stop amcat_worker || true

    if id amcat >/dev/null 2>&1; then
      deluser --remove-home amcat
    fi

    su postgres -c "dropdb --if-exists amcat"
    dpkg --purge elasticsearch
    rm -rf /usr/share/elasticsearch
    uninstall
}

setup_user(){
    # Check if user 'amcat' already exists
    if id amcat >/dev/null 2>&1; then
        return 0;
    fi

    # Add UNIX user amcat
    adduser -q --disabled-password --gecos "" amcat
}

setup_amcat(){
    start=$(pwd)

    # Make sure git is installed
    apt install -y git

    rm -rf ${INSTALL_DIR}
    mkdir -p ${INSTALL_DIR}
    cd ${INSTALL_DIR}
    #git clone https://github.com/amcat/amcat.git
    cp -ap /home/martijn/code/amcat .
    cd amcat
    rm -rf env
    #git checkout ${BRANCH}

    # Prevent unnecessary compilations
    apt install -y $(grep python3 requirements.apt.txt)

    # Build dependencies
    apt install -y $(cat apt_requirements.txt)

    # Build virtualenv, install dependencies
    python3 -m venv --system-site-packages env
    env/bin/python -m pip install wheel
    env/bin/python -m pip install -r requirements.txt

    # Install npm/bower/static files
    apt install nodejs-legacy npm -y
    npm install -g bower
    chown amcat:amcat -R ${INSTALL_DIR}
    su amcat -c "bower install"

    env/bin/python -m amcat.manage collectstatic --no-input -v 0

    # Copy configuration files
    rm -rf /etc/amcat
    mkdir -p /etc/amcat
    touch /etc/amcat/amcat.ini
    chmod 640 /etc/amcat/amcat.ini
    chown root:amcat /etc/amcat/amcat.ini

    while read p; do
      if [[ "${p}" =~ "#" ]] || [[ "${p}" =~ "[" ]] || [[ "${p}" == "" ]]; then
        echo "${p}" >> /etc/amcat/amcat.ini;
      else
        echo "#${p}" >> /etc/amcat/amcat.ini;
      fi
    done <settings/amcat.ini

    # Set user permissions
    chown amcat:amcat -R ${INSTALL_DIR}

    # Create logging directory
    mkdir -p /var/log/amcat
    chown -R root:amcat /var/log/amcat
    chmod -R 770 /var/log/amcat

    # Copy service file for systemd
    INSTALL_DIR=${INSTALL_DIR} envsubst < config/systemd/amcat.service > /lib/systemd/system/amcat.service
    INSTALL_DIR=${INSTALL_DIR} envsubst < config/systemd/amcat_worker.service > /lib/systemd/system/amcat_worker.service
    systemctl daemon-reload
    systemctl enable amcat amcat_worker

    cd ${start}
}

setup_scraping(){
    start=$(pwd)

    cd ${INSTALL_DIR}
    git clone https://github.com/amcat/amcat-scraping.git
    ln -s ${INSTALL_DIR}amcat/amcat ${INSTALL_DIR}amcat-scraping

    echo '#!/bin/bash' > scrape
    echo 'cd ~/amcat-scraping' >> scrape
    echo '../amcat/env/bin/python -m amcatscraping.scrape $@' >> scrape
    chmod +x scrape

    cd amcat-scraping
    ../amcat/env/bin/python -m pip install -r requirements.txt

    cd ${start}
}

setup_database(){
    start=$(pwd)

    su postgres -c "createuser -s amcat" || true
    su postgres -c "createdb amcat -O amcat" || true
    cd ${INSTALL_DIR}amcat
    sudo su amcat -c "env/bin/python -m amcat.manage migrate --no-input"

    cd ${start}
}

setup_elasticsearch(){
    start=$(pwd)

    wget ${ELASTIC_URL}
    dpkg -i elasticsearch-${ELASTIC_VERSION}.deb
    rm elasticsearch-${ELASTIC_VERSION}.deb

    # Install plugins
    cd /usr/share/elasticsearch
    systemctl stop elasticsearch
    bin/plugin remove analysis-icu || true
    bin/plugin remove head || true
    bin/plugin remove hitcount || true
    bin/plugin install mobz/elasticsearch-head
    bin/plugin install analysis-icu
    bin/plugin install amcat/hitcount/${ELASTIC_VERSION}

    # Enable hitcount as default similarity provider, and enable groovy scripting
    echo >> /etc/elasticsearch/elasticsearch.yml
    echo "index.similarity.default.type: hitcountsimilarity" >> /etc/elasticsearch/elasticsearch.yml
    echo "script.inline: on" >> /etc/elasticsearch/elasticsearch.yml
    echo "script.update: on" >> /etc/elasticsearch/elasticsearch.yml

    systemctl start elasticsearch

    cd ${start}
}

setup_nginx(){
    start=$(pwd)
    cd ${INSTALL_DIR}amcat

    apt install -y nginx letsencrypt uwsgi-plugin-python3 openssl
    mkdir -p /etc/nginx/ssl/
    chmod -R 600 /etc/nginx/ssl

    if [ ! -f /etc/nginx/ssl/dhparam.pem ]; then
        openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
    fi

    rm -f /etc/nginx/sites-enabled/default
    HOSTNAME=${hostname} INSTALL_DIR=${INSTALL_DIR} envsubst < config/nginx/amcat.conf > /etc/nginx/sites-available/amcat
    INSTALL_DIR=${INSTALL_DIR} envsubst < config/uwsgi/amcat.ini > /etc/amcat/uwsgi.ini
    mkdir -p /var/www/acme-challenges/${hostname}/.well-known/acme-challenge/

    if [ ! -f /etc/nginx/sites-enabled/amcat ]; then
        ln -s /etc/nginx/sites-available/amcat /etc/nginx/sites-enabled/amcat
    fi

    # Generate self-signed certificates
    if [ ! -f /etc/nginx/ssl/server.key ]; then
        openssl genrsa -des3 -passout pass:x -out /etc/nginx/ssl/server.pass.key 2048
        openssl rsa -passin pass:x -in /etc/nginx/ssl/server.pass.key -out /etc/nginx/ssl/server.key
        rm /etc/nginx/ssl/server.pass.key
        openssl req -new -key /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.csr -subj "/C=NL/ST=Example/L=Example/O=Example/OU=Example/CN=${hostname}"
        openssl x509 -req -days 365 -in /etc/nginx/ssl/server.csr -signkey /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.crt
    fi

    systemctl restart nginx

    #letsencrypt certonly --webroot -w /var/www/acme-challenges/${hostname}/ -d ${hostname}
    #sed -i '/DELETE_AFTER/d' /etc/nginx/sites-available/amcat
    #sed -i '/#ssl_certificate/ssl_certificate/g' /etc/nginx/sites-available/amcat

    systemctl restart nginx

    cd ${start}
}


#uninstall
echo "Setting up user amcat"
setup_user

echo "Setting up AmCAT.."
setup_amcat

echo "Setting up database.."
setup_database

echo "Setting up elasticsearch.."
setup_elasticsearch

echo "Setting up nginx.."
setup_nginx

systemctl start amcat