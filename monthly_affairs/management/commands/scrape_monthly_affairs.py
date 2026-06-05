import requests

from django.core.management.base import BaseCommand, CommandError

from monthly_affairs.services import MonthlyAffairsScraper


class Command(BaseCommand):
    help = 'Scrape Uttoron Monthly Affairs and sync it into the local database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-rebuild',
            action='store_true',
            help='Rebuild stored blocks even if the content hash did not change.',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Optional year override. Defaults to the current year.',
        )
        parser.add_argument(
            '--month',
            help='Optional English month override like April. Defaults to the current month.',
        )

    def handle(self, *args, **options):
        scraper = MonthlyAffairsScraper()
        try:
            result = scraper.sync(
                force_rebuild=options['force_rebuild'],
                target_year=options.get('year'),
                target_month_name=options.get('month'),
            )
        except requests.RequestException as exc:
            raise CommandError(f'Network error while scraping Monthly Affairs: {exc}')
        except Exception as exc:
            raise CommandError(f'Monthly Affairs sync failed: {exc}')

        self.stdout.write(
            self.style.SUCCESS(
                'Monthly Affairs sync completed: '
                f"parsed={result['parsed']}, "
                f"created={result['created']}, "
                f"updated={result['updated']}, "
                f"skipped={result['skipped']}"
            )
        )
