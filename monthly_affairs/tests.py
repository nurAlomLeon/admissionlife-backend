from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import MonthlyAffairsBlock, MonthlyAffairsIssue
from .services import MonthlyAffairsScraper


SAMPLE_HTML = """
<div id="MonthlyAffairsDetails">
  <section class="py-3 post-item description-div" data-creationDate="5/13/2026 4:10:42 PM" data-category="Bangladesh" data-year="2026" data-month="April">
    <h3><b>বাংলাদেশ বিষয়াবলি</b></h3>
    <div class="d-flex align-items-center">
      <h5 class="category">Bangladesh</h5>
      <h5 class="date ml-2">April, 2026</h5>
    </div>
    <div style="text-align: center;"><iframe src="https://www.youtube.com/embed/example"></iframe></div>
    <div>
      <h2><strong>কালানুক্রমিক ঘটনাবলি</strong></h2>
      <p><b>০৫ এপ্রিল ২০২৬</b></p>
      <p>♦ দেশের ১৮টি জেলার ৩০টি উপজেলায় হামের বিশেষ টিকাদান কর্মসূচি শুরু।</p>
      <p>♦ ঢাকা বিশ্ববিদ্যালয়ের চারুকলা অনুষদের শোভাযাত্রার নাম পরিবর্তন করে 'বৈশাখী শোভাযাত্রা' করা হয়।</p>
      <h2><strong>পুরস্কার ও সম্মাননা</strong></h2>
      <p><strong>MBE সম্মাননা</strong></p>
      <p>সমাজসেবা ও দাতব্য কার্যক্রমে অসামান্য অবদানের স্বীকৃতি স্বরূপ যুক্তরাজ্যের সম্মানসূচক MBE উপাধিতে ভূষিত হন আবু তাহের।</p>
      <table>
        <tr><th>নাম</th><th>অবস্থা</th></tr>
        <tr><td>সিটি সেন্টার</td><td>চালু</td></tr>
      </table>
    </div>
  </section>
</div>
"""


class MonthlyAffairsScraperTests(TestCase):
    def test_parse_html_extracts_issue_and_blocks(self):
        scraper = MonthlyAffairsScraper()

        issues = scraper.parse_html(SAMPLE_HTML)

        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.source_category, 'Bangladesh')
        self.assertEqual(issue.month_name, 'April')
        self.assertEqual(issue.month_number, 4)
        self.assertEqual(issue.year, 2026)
        self.assertEqual(issue.embed_url, '')
        self.assertGreaterEqual(len(issue.blocks), 6)

        date_block = next(block for block in issue.blocks if block.block_type == 'DATE')
        self.assertEqual(date_block.event_date, date(2026, 4, 5))

        bullet_blocks = [block for block in issue.blocks if block.block_type == 'BULLET']
        self.assertEqual(len(bullet_blocks), 2)
        self.assertEqual(bullet_blocks[0].event_date, date(2026, 4, 5))

        table_block = next(block for block in issue.blocks if block.block_type == 'TABLE')
        self.assertEqual(table_block.table_data['headers'], ['নাম', 'অবস্থা'])
        self.assertEqual(table_block.table_data['rows'], [['সিটি সেন্টার', 'চালু']])

    @patch('monthly_affairs.services.requests.get')
    def test_sync_creates_and_updates_issues(self, mock_get):
        response = Mock()
        response.text = SAMPLE_HTML
        response.encoding = 'utf-8'
        response.raise_for_status = Mock()
        mock_get.return_value = response

        scraper = MonthlyAffairsScraper()
        first = scraper.sync(target_year=2026, target_month_name='April')
        second = scraper.sync(target_year=2026, target_month_name='April')

        self.assertEqual(first['created'], 1)
        self.assertEqual(second['skipped'], 1)

        issue = MonthlyAffairsIssue.objects.get(
            source_category='Bangladesh',
            year=2026,
            month_name='April',
        )
        self.assertEqual(issue.blocks.count(), 8)


class MonthlyAffairsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='affairs',
            password='testpass123',
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.issue = MonthlyAffairsIssue.objects.create(
            source_category='Bangladesh',
            year=2026,
            month_name='June',
            month_number=6,
            title='বাংলাদেশ বিষয়াবলি',
            subtitle_category='Bangladesh',
            subtitle_month_label='June, 2026',
            source_url='https://uttoron.academy/MonthlyAffairs',
            embed_url='https://www.youtube.com/embed/example',
            content_hash='hash',
            raw_html='<section></section>',
        )
        MonthlyAffairsBlock.objects.create(
            issue=self.issue,
            order=1,
            block_type=MonthlyAffairsBlock.BlockType.HEADING,
            title='কালানুক্রমিক ঘটনাবলি',
        )
        MonthlyAffairsBlock.objects.create(
            issue=self.issue,
            order=2,
            block_type=MonthlyAffairsBlock.BlockType.BULLET,
            text='নতুন একটি ঘটনা যোগ হয়েছে।',
        )

    def test_issue_list_returns_summary_fields(self):
        response = self.client.get('/api/monthly-affairs/issues/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.issue.id)
        self.assertEqual(response.data[0]['source_category'], 'Bangladesh')
        self.assertEqual(response.data[0]['block_count'], 2)
        self.assertEqual(response.data[0]['preview_text'], 'নতুন একটি ঘটনা যোগ হয়েছে।')

    def test_issue_detail_returns_blocks(self):
        response = self.client.get(f'/api/monthly-affairs/issues/{self.issue.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.issue.id)
        self.assertEqual(len(response.data['blocks']), 2)
