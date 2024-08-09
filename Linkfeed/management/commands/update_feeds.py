from django.core.management.base import BaseCommand
from Linkfeed.views import refresh_mirrored_rss_feed
from Linkfeed.models import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        rss_feeds = RSSFeed.objects.all()

        for feed in rss_feeds:
            user = feed.user
            refresh_mirrored_rss_feed(user, feed)
        
        print('All feeds updated')