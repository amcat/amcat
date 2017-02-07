# This is a comment
FROM ubuntu:16.04
MAINTAINER Wouter van Atteveldt (wouter@vanatteveldt.com)
EXPOSE 8000

RUN apt-get -qq update && apt-get install -y antiword unrtf python3-dev libxml2-dev libxslt-dev graphviz pspp redis-server r-base python3-lxml python3-amqplib python3-psycopg2 python3-requests python3-pygments git python3 python3-pip postgresql-client-9.5 
RUN pip3 install git+git://github.com/amcat/amcat.git
RUN mkdir -p /etc/amcat
ADD amcat.ini run.sh /etc/amcat/


CMD bash /etc/amcat/run.sh

