#inverting bzk aliases dict
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES

if __name__ == '__main__':

    new_dict = {}
    for entry in BZK_ALIASES.items():
        for alias in entry[1]:
            new_dict[alias] = entry[0]
    print(new_dict)

    # WVA: WAAROM STAAT DIT HIER? IS DIT NIET HETZELFDE ALS HET SCRIPT IN MAINTENANCE/TMP?
    # ALS DAT ZO IS, GAARNA HG RM'EN!
