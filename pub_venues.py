#!python3

from scholarly import scholarly
from scholarly import ProxyGenerator
from pybliometrics.scopus import ScopusSearch

import re
import json
import argparse
import sys

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-t", "--title", help="paper title")
group.add_argument("-r", "--references", help="JSON file with list of references (from anystyle)")

args = parser.parse_args()

papers_list = []

if args.title:

    papers_list.append(args.title)

elif args.references:

    with open(args.references) as f:

        data = json.load(f)

        for paper in data:

            if 'date' in paper and 'title' in paper:

                year = int(paper['date'][0])

                if year >= 2010:

                    title = paper['title'][-1]

                    title = re.sub(r'\s\d+\s', ' ', title)

                    print("Reference found: {}".format(title))

                    papers_list.append(title)

else:
    parser.print_help()
    sys.exit(0)



venues = []


pg = ProxyGenerator()
pg.Tor_Internal(tor_cmd = "/Applications/Tor Browser.app//Contents/Resources/TorBrowser/Tor/tor")
scholarly.use_proxy(pg)


for paper_title in papers_list:

    print("Searching for: {}".format(paper_title))

    pub_query = scholarly.search_pubs(paper_title)
    pub = scholarly.fill(next(pub_query))

    for citation in scholarly.citedby(pub):
        pub_title = citation['bib']['title']
        pub_year = citation['bib']['pub_year']

        print("")
        print("------------------------")
        print("TITLE: {}".format(pub_title))
        print("YEAR: {}".format(pub_year))

        scopus_query = re.sub("[^a-zA-Z0-9-\s]+", "", pub_title)

        if not scopus_query:
            print("Paper title not processable, skipping...")
            continue

        s = ScopusSearch('TITLE ( "{}" ) '.format(scopus_query))

        if s.results is None:
            print("Paper not found on Scopus, skipping...")
            continue

        scopus_paper = None
        scopus_paper_title_diff = 1000

        # If multiple result, pick the most similar one
        for scopus_result in s.results:

            if scopus_result.title is not None:

                diff = len(scopus_query) - len(scopus_result.title)

                if scopus_paper_title_diff < diff:

                    scopus_paper_title_diff = diff
                    scopus_paper = scopus_result

        pub_venue = scopus_paper.publicationName

        print("VENUE: {}".format(pub_venue))

        venues.append(pub_venue)


venues_names = {}

for venue in venues:

    m = re.search("([\w]+\s)*(Conference|Workshop|Symposium)\s?([\w,]+\s?)*", venue)

    if m is not None:

        conf_name = m.group(0)

        conf_name = re.sub("Proceedings(\sof)?(\sthe)?", "", conf_name)
        conf_name = re.sub("\d+(st|nd|rd|th)", "", conf_name)
        conf_name = re.sub("\s-\s", "", conf_name)
        conf_name = re.sub("\d{4}\s", "", conf_name)
        if len(re.findall(r'\w+', conf_name)) > 2:
            conf_name = re.sub("(,\s)?((IEEE|ACM)\s)?(\w*[A-Z]\w*[A-Z]\w*)(\s|')?(\d+)?", "", conf_name)
        conf_name = re.sub("^\s+", "", conf_name)
        conf_name = re.sub("\s+$", "", conf_name)

        venue = conf_name

    if venue in venues_names:
        venues_names[venue] = venues_names[venue] + 1
    else:
        venues_names[venue] = 1


sorted_keys = sorted(venues_names, key=venues_names.get, reverse=True)

for venue in sorted_keys:
    print("{} {}".format(venues_names[venue], venue))

