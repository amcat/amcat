#inverting bzk aliases dict
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES
new_dict = {}
for entry in BZK_ALIASES.items():
    for alias in entry[1]:
        new_dict[alias] = entry[0]
print(new_dict)
