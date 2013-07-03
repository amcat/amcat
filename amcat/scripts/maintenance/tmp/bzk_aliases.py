import json

from amcat.models.medium import Medium

alias_file = open('bzk_aliases.txt','r')
media = json.loads(alias_file.read())
alias_dict = {}
for medium, aliases in media.items():
    alias_dict[medium] = [Medium.objects.get(pk=alias).name for alias in aliases]

print(alias_dict)
