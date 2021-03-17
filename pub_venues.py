#!python3

from scholarly import scholarly
from scholarly import ProxyGenerator
from pybliometrics.scopus import ScopusSearch

import re
import json
import argparse
import sys
import os
import pickle

import urllib3
urllib3.disable_warnings()

caching_dir = "./caching"

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-t", "--title", help="paper title")
group.add_argument("-r", "--references", help="JSON file with list of references (from anystyle)")
parser.add_argument("-s", "--scaperapikey", help="Scaper API Key")

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


scholarly.set_timeout(60)
scholarly.set_logger(True)


if args.scaperapikey:
    scraper_api_key = '4534bcf18967639e886fbe7dcf300f04'

    pg = ProxyGenerator()
    pg.SingleProxy(http = f"http://scraperapi:{scraper_api_key}@proxy-server.scraperapi.com:8001", https = f"http://scraperapi:{scraper_api_key}@proxy-server.scraperapi.com:8001")
    scholarly.use_proxy(pg)

#pg = ProxyGenerator()
#pg.Tor_Internal(tor_cmd = "/usr/local/bin/tor")
#pg.Tor_External(tor_sock_port=9050, tor_control_port=9051, tor_password="scholarly_password")
#scholarly.use_proxy(pg)



if not os.path.isdir(caching_dir):
    os.mkdir(caching_dir)
    print("Created caching dir for Google Scholar queries")


for paper_title in papers_list:

    print("Searching for: {}".format(paper_title))

    citations = []
    num_citations = 0

    pub_serialized = os.path.join(caching_dir, paper_title + '.bin')
    citations_serialized = os.path.join(caching_dir, paper_title + '.citations.bin')
    iterator_serialized = os.path.join(caching_dir, paper_title + '.iterator.bin')

    if os.path.exists(citations_serialized):

        print("Reading citations from cache...")
        
        with open(citations_serialized, 'rb') as binfile:

            num_citations = pickle.load(binfile)

            while 1:
                try:
                    citations.append(pickle.load(binfile))
                except EOFError:
                    break



    if num_citations == 0 or len(citations) != num_citations:
        
        pub = None

        if os.path.exists(pub_serialized):

            print("Reading publication from cache...")
        
            with open(pub_serialized, 'rb') as binfile:

                pub = pickle.load(binfile)

        else:

            print("New query for publication...")

            pub_query = scholarly.search_single_pub(paper_title)
            pub = scholarly.fill(pub_query)

            print("Saving publication to cache...")

            with open(pub_serialized, 'wb') as binfile:

                pickle.dump(pub, binfile)



        num_citations = pub['num_citations']

        print(f"No. citations: {num_citations}")


        if num_citations == 0:
            print("Skipping the paper, no citations")
            continue


        while len(citations) < num_citations:

            print("Retrieving citations...")

            if not os.path.exists(citations_serialized):

                print("Creating new citation list cache...")

                with open(citations_serialized, 'wb') as cit_file:

                    pickle.dump(num_citations, cit_file)

            else:
                print("Appending to existing citation list cache...")


            with open(citations_serialized, 'ab') as cit_file:

                cit_iterator = scholarly.citedby(pub)

                if os.path.exists(iterator_serialized):

                    with open(iterator_serialized, 'rb') as iter_file:

                        iterator_state = pickle.load(iter_file)
            
                    print("Loading iter state: {}".format(iterator_state))

                    cit_iterator.__setstate__(iterator_state)



                for citation in cit_iterator:
            
                    print("Appending: {}".format(citation['bib']['title']))

                    citations.append(citation)
        
                    pickle.dump(citation, cit_file)

                    print("Dumping iter state: {}".format(cit_iterator.__getstate__()))

                    with open(iterator_serialized, 'wb') as iter_file:

                        pickle.dump(cit_iterator.__getstate__(), iter_file)



    for citation in citations:

        pub_title = citation['bib']['title']
        #pub_year = citation['bib']['pub_year']

        print("")
        print("------------------------")
        print("TITLE: {}".format(pub_title))

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

        # If multiple results, pick the most similar one
        for scopus_result in s.results:

            if scopus_result.title is not None:

                diff = abs(len(scopus_query) - len(scopus_result.title))

                if diff < scopus_paper_title_diff:

                    scopus_paper_title_diff = diff
                    scopus_paper = scopus_result

        pub_venue = scopus_paper.publicationName
        pub_year = scopus_paper.coverDate


        print("YEAR: {}".format(pub_year)).str[:4]
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

