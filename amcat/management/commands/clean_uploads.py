from django.core.management import BaseCommand
from amcat.models import UploadedFile
from logging import getLogger

log = getLogger(__name__)

class Command(BaseCommand):
    help = "Delete all expired upload objects and associated files."
    def handle(self, *args, **options):
        n = UploadedFile.delete_expired().count()
        log.info("Deleted {} records.".format(n))
