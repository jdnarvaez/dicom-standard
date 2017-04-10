'''
Common functions for extracting information from the
DICOM standard HTML file.
'''

import json
import re
import sys
from functools import partial

from bs4 import BeautifulSoup
from bs4 import NavigableString

import parse_relations as pr

BASE_DICOM_URL = "http://dicom.nema.org/medical/dicom/current/output/html/"
BASE_SHORT_DICOM_SECTION_URL = "http://dicom.nema.org/medical/dicom/current/output/chtml/"
SHORT_DICOM_URL_PREFIX = "http://dicom.nema.org/medical/dicom/current/output/chtml/part03/"

allowed_attributes = ["href", "src", "type", "data", "colspan", "rowspan"]

def parse_html_file(filepath):
    with open(filepath, 'r') as html_file:
        return BeautifulSoup(html_file, 'html.parser')


def write_pretty_json(data):
    json.dump(data, sys.stdout, sort_keys=False, indent=4, separators=(',', ':'))


def read_json_to_dict(filepath):
    with open(filepath, 'r') as json_file:
        json_string = json_file.read()
        json_dict = json.loads(json_string)
        return json_dict


def all_tdivs_in_chapter(standard, chapter_name):
    chapter_divs = standard.find_all('div', class_='chapter')
    for chapter in chapter_divs:
        if chapter.div.div.div.h1.a.get('id') == chapter_name:
            table_divs = chapter.find_all('div', class_='table')
            return table_divs


def create_slug(title):
    first_pass = re.sub(r'[\s/]+', '-', title.lower())
    return re.sub(r'[\(\),\']+', '', first_pass)


def find_tdiv_by_id(all_tables, table_id):
    table_with_id = [table for table in all_tables if pr.table_id(table) == table_id]
    return None if table_with_id == [] else table_with_id[0]


def clean_table_name(name):
    _, _, title = re.split('\u00a0', name)
    possible_table_suffixes = r'(IOD Modules)|(Module Attributes)|(Macro Attributes)|(Module Table)'
    clean_title, *_ = re.split(possible_table_suffixes, title)
    return clean_title.strip()


def clean_html(html):
    parsed_html = BeautifulSoup(html, 'html.parser')
    top_level_tag = get_top_level_tag(parsed_html)
    remove_attributes_from_html_tags(top_level_tag)
    remove_empty_children(top_level_tag)
    return resolve_relative_resource_urls(str(top_level_tag))


def get_top_level_tag(parsed_html):
    return next(parsed_html.descendants)


def remove_attributes_from_html_tags(top_level_tag):
    clean_tag_attributes(top_level_tag)
    for child in top_level_tag.descendants:
        clean_tag_attributes(child)


def clean_tag_attributes(tag):
    if not isinstance(tag, NavigableString):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed_attributes}


def remove_empty_children(top_level_tag):
    empty_anchor_tags = filter((lambda a: a.text == ''), top_level_tag.find_all('a'))
    for anchor in empty_anchor_tags:
        anchor.decompose()


def resolve_relative_resource_urls(html_string):
    html = BeautifulSoup(html_string, 'html.parser')
    anchors = html.find_all('a', href=True)
    imgs = html.find_all("img", src=True)
    equations = html.find_all("object", data=True)
    list(map(update_anchor_href, anchors))
    list(map(partial(resolve_resource, 'src'), imgs))
    list(map(partial(resolve_resource, 'data'), equations))
    return str(html)


def update_anchor_href(anchor):
    if not has_protocol_prefix(anchor, 'href'):
        anchor['href'] = resolve_href_url(anchor['href'])
        anchor['target'] = '_blank'


def has_protocol_prefix(resource, url_attribute):
    return re.match(r'(http)|(ftp)', resource[url_attribute])


def resolve_href_url(href):
    if re.match(r'(.*sect_.*)|(.*chapter.*)', href):
        return BASE_SHORT_DICOM_SECTION_URL + get_short_html_location(href)
    else:
        return BASE_DICOM_URL + get_long_html_location(href)


def get_short_html_location(reference_link):
    standard_page, section_id = reference_link.split('#')
    chapter_with_extension = 'part03.html' if standard_page == '' else standard_page
    chapter, _ = chapter_with_extension.split('.html')
    return chapter + '/' + get_standard_page(section_id) + '.html#' + section_id


def get_standard_page(sect_id):
    sections = sect_id.split('.')
    try:
        cutoff_index = sections.index('1')
        cropped_section = sections[0:cutoff_index]
        section_page = '.'.join(sections[0:cutoff_index])
        if len(cropped_section) == 1:
            section_page = section_page.replace('sect_', 'chapter_')
        return section_page
    except ValueError:
        return sect_id


def get_long_html_location(reference_link):
    standard_page, section_id = reference_link.split('#')
    chapter_with_extension = 'part03.html' if standard_page == '' else standard_page
    return chapter_with_extension + '#' + section_id

def resolve_resource(url_attribute, resource):
    if not has_protocol_prefix(resource, url_attribute):
        resource[url_attribute] = BASE_DICOM_URL + resource[url_attribute]


def text_from_html_string(html_string):
    parsed_html = BeautifulSoup(html_string, 'html.parser')
    return parsed_html.text.strip()


def table_parent_page(table_div):
    parent_section_id = table_div.parent.div.div.div.find('a').get('id')
    sections = parent_section_id.split('.')
    try:
        cutoff_index = sections.index('1')
        return '.'.join(sections[0:cutoff_index])
    except ValueError:
        return parent_section_id


