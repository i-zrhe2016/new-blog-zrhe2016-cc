from django.core.management.base import BaseCommand, CommandError
from blogs.content_store import export_content


class Command(BaseCommand):
    help = 'Export personal blog content into versionable Markdown files.'

    def add_arguments(self, parser):
        parser.add_argument('directory', nargs='?')

    def handle(self, *args, **options):
        try:
            count = export_content(options['directory'])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Exported {count} articles and pages')
