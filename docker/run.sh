createdb -h postgres -U postgres amcat
set -e
python3 -m amcat.manage migrate
python3 -m amcat.manage runserver
