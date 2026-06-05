from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.db import transaction
from django.utils import timezone

from .models import MonthlyAffairsBlock, MonthlyAffairsIssue


@dataclass
class ParsedBlock:
    order: int
    block_type: str
    heading_level: int | None = None
    section_heading: str = ''
    title: str = ''
    text: str = ''
    event_date: date | None = None
    table_data: dict[str, Any] | None = None
    media_url: str = ''
    metadata: dict[str, Any] | None = None
    raw_html: str = ''


@dataclass
class ParsedIssue:
    source_category: str
    year: int
    month_name: str
    month_number: int | None
    title: str
    subtitle_category: str
    subtitle_month_label: str
    source_created_at: datetime | None
    source_url: str
    embed_url: str
    raw_html: str
    content_hash: str
    blocks: list[ParsedBlock]


class MonthlyAffairsScraper:
    SOURCE_URL = 'https://uttoron.academy/MonthlyAffairs'
    REQUEST_TIMEOUT = 45
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/127.0 Safari/537.36'
    )
    BULLET_PREFIX_RE = re.compile(r'^[♦•●◦\-–—]+\s*')
    DATE_RE = re.compile(r'^(?P<day>\d{1,2})\s+(?P<month>[^\s]+)\s+(?P<year>\d{4})$')
    MONTH_MAP = {
        'january': 1,
        'february': 2,
        'march': 3,
        'april': 4,
        'may': 5,
        'june': 6,
        'july': 7,
        'august': 8,
        'september': 9,
        'october': 10,
        'november': 11,
        'december': 12,
        'জানুয়ারি': 1,
        'ফেব্রুয়ারি': 2,
        'মার্চ': 3,
        'এপ্রিল': 4,
        'মে': 5,
        'জুন': 6,
        'জুলাই': 7,
        'আগস্ট': 8,
        'সেপ্টেম্বর': 9,
        'অক্টোবর': 10,
        'নভেম্বর': 11,
        'ডিসেম্বর': 12,
    }
    BANGLA_DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')

    def fetch_html(
        self,
        *,
        target_year: int | None = None,
        target_month_name: str | None = None,
    ) -> str:
        response = self._get(self.SOURCE_URL)
        response.raise_for_status()
        response.encoding = response.encoding or 'utf-8'
        return response.text

    def parse_html(self, html: str) -> list[ParsedIssue]:
        soup = BeautifulSoup(html, 'html.parser')
        sections = soup.select('#MonthlyAffairsDetails > section.post-item')
        if not sections:
            raise ValueError('No Monthly Affairs sections found in source HTML.')

        parsed_issues = []
        for section in sections:
            issue = self._parse_issue_section(section)
            if issue is not None:
                parsed_issues.append(issue)
        return parsed_issues

    def sync(
        self,
        *,
        force_rebuild: bool = False,
        target_year: int | None = None,
        target_month_name: str | None = None,
    ) -> dict[str, int]:
        html = self.fetch_html(
            target_year=target_year,
            target_month_name=target_month_name,
        )
        parsed_issues = self.parse_html(html)

        if target_year is None or target_month_name is None:
            current_date = timezone.localdate()
            target_year = current_date.year
            target_month_name = current_date.strftime('%B')

        parsed_issues = [
            issue for issue in parsed_issues
            if issue.year == target_year and issue.month_name == target_month_name
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for parsed in parsed_issues:
                issue, created = MonthlyAffairsIssue.objects.get_or_create(
                    source_category=parsed.source_category,
                    year=parsed.year,
                    month_name=parsed.month_name,
                    defaults=self._issue_defaults(parsed),
                )

                if created:
                    self._replace_blocks(issue, parsed.blocks)
                    created_count += 1
                    continue

                should_rebuild = (
                    force_rebuild
                    or issue.content_hash != parsed.content_hash
                    or issue.raw_html != parsed.raw_html
                    or issue.embed_url != parsed.embed_url
                )

                for field, value in self._issue_defaults(parsed).items():
                    setattr(issue, field, value)
                issue.save()

                if should_rebuild:
                    self._replace_blocks(issue, parsed.blocks)
                    updated_count += 1
                else:
                    skipped_count += 1

        return {
            'parsed': len(parsed_issues),
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
        }

    def _issue_defaults(self, parsed: ParsedIssue) -> dict[str, Any]:
        return {
            'month_number': parsed.month_number,
            'title': parsed.title,
            'subtitle_category': parsed.subtitle_category,
            'subtitle_month_label': parsed.subtitle_month_label,
            'source_created_at': parsed.source_created_at,
            'source_url': parsed.source_url,
            'embed_url': parsed.embed_url,
            'raw_html': parsed.raw_html,
            'content_hash': parsed.content_hash,
        }

    def _replace_blocks(self, issue: MonthlyAffairsIssue, blocks: list[ParsedBlock]) -> None:
        issue.blocks.all().delete()
        MonthlyAffairsBlock.objects.bulk_create([
            MonthlyAffairsBlock(
                issue=issue,
                order=block.order,
                block_type=block.block_type,
                heading_level=block.heading_level,
                section_heading=block.section_heading,
                title=block.title,
                text=block.text,
                event_date=block.event_date,
                table_data=block.table_data,
                media_url=block.media_url,
                metadata=block.metadata or {},
                raw_html=block.raw_html,
            )
            for block in blocks
        ])

    def _parse_issue_section(self, section: Tag) -> ParsedIssue | None:
        source_category = (section.get('data-category') or '').strip()
        month_name = (section.get('data-month') or '').strip()
        year_value = (section.get('data-year') or '').strip()
        if not source_category or not month_name or not year_value:
            return None

        title = self._clean_text(section.find('h3').get_text(' ', strip=True) if section.find('h3') else '')
        labels = section.select('h5')
        subtitle_category = self._clean_text(labels[0].get_text(' ', strip=True)) if len(labels) > 0 else ''
        subtitle_month_label = self._clean_text(labels[1].get_text(' ', strip=True)) if len(labels) > 1 else ''
        source_created_at = self._parse_source_created_at(section.get('data-creationDate'))
        month_number = self.MONTH_MAP.get(month_name.lower()) or self.MONTH_MAP.get(month_name)

        blocks: list[ParsedBlock] = []
        current_heading = ''
        current_event_date: date | None = None
        order = 1

        for child in section.children:
            if not isinstance(child, Tag):
                continue
            if child.name in {'h3'}:
                continue
            if child.name == 'div' and child.get('class') and 'd-flex' in child.get('class', []):
                continue

            for parsed in self._extract_blocks_from_node(
                child,
                current_heading=current_heading,
                current_event_date=current_event_date,
            ):
                parsed.order = order
                order += 1
                if parsed.block_type == MonthlyAffairsBlock.BlockType.HEADING:
                    current_heading = parsed.title
                elif parsed.block_type == MonthlyAffairsBlock.BlockType.DATE:
                    current_event_date = parsed.event_date
                blocks.append(parsed)

        raw_html = str(section)
        content_hash = hashlib.sha256(raw_html.encode('utf-8')).hexdigest()

        return ParsedIssue(
            source_category=source_category,
            year=int(year_value),
            month_name=month_name,
            month_number=month_number,
            title=title,
            subtitle_category=subtitle_category,
            subtitle_month_label=subtitle_month_label,
            source_created_at=source_created_at,
            source_url=self.SOURCE_URL,
            embed_url='',
            raw_html=raw_html,
            content_hash=content_hash,
            blocks=blocks,
        )

    def _extract_blocks_from_node(
        self,
        node: Tag,
        *,
        current_heading: str,
        current_event_date: date | None,
    ) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []

        if node.name == 'iframe':
            return blocks

        if node.name == 'img':
            src = self._absolute_url(node.get('src', ''))
            if src:
                blocks.append(ParsedBlock(
                    order=0,
                    block_type=MonthlyAffairsBlock.BlockType.IMAGE,
                    media_url=src,
                    section_heading=current_heading,
                    raw_html=str(node),
                ))
            return blocks

        if node.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            text = self._clean_text(node.get_text(' ', strip=True))
            if text:
                blocks.append(ParsedBlock(
                    order=0,
                    block_type=MonthlyAffairsBlock.BlockType.HEADING,
                    heading_level=int(node.name[1]),
                    title=text,
                    section_heading=current_heading,
                    raw_html=str(node),
                ))
            return blocks

        if node.name == 'p':
            parsed = self._parse_paragraph(node, current_heading, current_event_date)
            return [parsed] if parsed else []

        if node.name in {'ul', 'ol'}:
            for item in node.find_all('li', recursive=False):
                text = self._clean_text(item.get_text(' ', strip=True))
                if not text:
                    continue
                blocks.append(ParsedBlock(
                    order=0,
                    block_type=MonthlyAffairsBlock.BlockType.BULLET,
                    text=text,
                    event_date=current_event_date,
                    section_heading=current_heading,
                    raw_html=str(item),
                ))
            return blocks

        if node.name == 'table':
            table_data = self._parse_table(node)
            blocks.append(ParsedBlock(
                order=0,
                block_type=MonthlyAffairsBlock.BlockType.TABLE,
                table_data=table_data,
                section_heading=current_heading,
                raw_html=str(node),
            ))
            return blocks

        local_heading = current_heading
        local_event_date = current_event_date
        for child in node.children:
            if isinstance(child, Tag):
                child_blocks = self._extract_blocks_from_node(
                    child,
                    current_heading=local_heading,
                    current_event_date=local_event_date,
                )
                blocks.extend(child_blocks)
                for parsed in child_blocks:
                    if parsed.block_type == MonthlyAffairsBlock.BlockType.HEADING:
                        local_heading = parsed.title
                    elif parsed.block_type == MonthlyAffairsBlock.BlockType.DATE:
                        local_event_date = parsed.event_date

        return blocks

    def _parse_paragraph(
        self,
        node: Tag,
        current_heading: str,
        current_event_date: date | None,
    ) -> ParsedBlock | None:
        text = self._clean_text(node.get_text(' ', strip=True))
        if not text or text == 'No more data found.':
            return None

        parsed_date = self._parse_event_date(text)
        if parsed_date is not None:
            return ParsedBlock(
                order=0,
                block_type=MonthlyAffairsBlock.BlockType.DATE,
                title=text,
                text=text,
                event_date=parsed_date,
                section_heading=current_heading,
                raw_html=str(node),
            )

        if self._is_bullet_text(text):
            return ParsedBlock(
                order=0,
                block_type=MonthlyAffairsBlock.BlockType.BULLET,
                text=self.BULLET_PREFIX_RE.sub('', text).strip(),
                event_date=current_event_date,
                section_heading=current_heading,
                raw_html=str(node),
            )

        return ParsedBlock(
            order=0,
            block_type=MonthlyAffairsBlock.BlockType.PARAGRAPH,
            text=text,
            event_date=current_event_date,
            section_heading=current_heading,
            raw_html=str(node),
        )

    def _parse_table(self, table: Tag) -> dict[str, Any]:
        rows = []
        headers: list[str] = []

        tr_nodes = table.find_all('tr')
        for index, row in enumerate(tr_nodes):
            cells = row.find_all(['th', 'td'])
            cleaned = [self._clean_text(cell.get_text(' ', strip=True)) for cell in cells]
            if not any(cleaned):
                continue
            if index == 0 and row.find_all('th'):
                headers = cleaned
            else:
                rows.append(cleaned)

        if not headers and rows:
            headers = rows.pop(0)

        return {
            'headers': headers,
            'rows': rows,
        }

    def _parse_source_created_at(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), '%m/%d/%Y %I:%M:%S %p')
        except ValueError:
            return None

    def _parse_event_date(self, text: str) -> date | None:
        normalized = self._normalize_digits(text)
        normalized = normalized.replace(',', ' ')
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        match = self.DATE_RE.match(normalized)
        if not match:
            return None

        day = int(match.group('day'))
        month_token = match.group('month').strip()
        year = int(match.group('year'))
        month_number = self.MONTH_MAP.get(month_token.lower()) or self.MONTH_MAP.get(month_token)
        if month_number is None:
            return None

        try:
            return date(year, month_number, day)
        except ValueError:
            return None

    def _is_bullet_text(self, text: str) -> bool:
        return bool(self.BULLET_PREFIX_RE.match(text))

    def _normalize_digits(self, text: str) -> str:
        return text.translate(self.BANGLA_DIGITS)

    def _clean_text(self, text: str) -> str:
        text = text.replace('\xa0', ' ')
        text = text.replace('\u200b', '')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _absolute_url(self, value: str) -> str:
        if not value:
            return ''
        return urljoin(self.SOURCE_URL, value)

    def _section_key(self, section: Tag) -> tuple[str, str, str] | None:
        category = (section.get('data-category') or '').strip()
        year = (section.get('data-year') or '').strip()
        month = (section.get('data-month') or '').strip()
        if not category or not year or not month:
            return None
        return (category, year, month)

    def _get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        return requests.get(
            url,
            params=params,
            timeout=self.REQUEST_TIMEOUT,
            headers={'User-Agent': self.USER_AGENT},
        )
