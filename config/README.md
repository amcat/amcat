
This folder contains example config files for setting up AmCAT as a service, e.g. to run it as a permanent web service on port 80. 
Files are included for using nginx as a web server, and for setting up the WSGI server using uwsgi using both systemd and for upstart. 

These are meant as examples, and not as step-by-step instructions.
In particular, these files will need to be edited to reflect the specifics of a server, i.e. the correct paths, elastic/db hosts, passwords etc.

To install nginx and uwsgi on a debian/ubuntu server, you can run:

```
sudo apt-get install nginx uwsgi uwsgi-plugin-python
```

The config files assume that you set up the database and elastic as outlined in the global README, and install amcat in /srv/amcat/amcat with the virtualenv in /srv/amcat/env. 
You can also choose to setup the database and elastic on separate hosts, and in fact it is recommended to setup elastic on multiple nodes. In that case, simply point the database/elastic hosts to the correct hostnames or IP address.
