#!/usr/bin/python
# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import sys
import time
import os
import logging
import argparse
import requests
import codecs
import json

base_url = "http://www.tripadvisor.com"
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36"


parser = argparse.ArgumentParser(description='Scrape tripadvisor')
parser.add_argument('-datadir', type=str, help='Direcotry to store row html files', default = "data/")
parser.add_argument('-state', type=str, help='State for which the city data is required.', required=True)
parser.add_argument('-city', type=str, help='City for which the city data is required.', required=True)
parser.add_argument('-v','--verbose',help="Set log level to debug", action="store_true")

args = parser.parse_args()


log = logging.getLogger(__name__)
log.setLevel(logging.ERROR)
if args.verbose:
    log.setLevel(logging.DEBUG)
loghandler = logging.StreamHandler(sys.stderr)
loghandler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
log.addHandler(loghandler)


""" STEP 1  """
def get_tourism_page(city, state):
	""" 
		Return the json containing the
		URL of the tourism city page
	"""

	# EXAMPLE: http://www.tripadvisor.com/TypeAheadJson?query=boston%20massachusetts&action=API
	#          http://www.tripadvisor.com//TypeAheadJson?query=san%20francisco%20california&type=GEO&action=API
	url = "%s/TypeAheadJson?query=%s%%20%s&action=API" % (base_url, "%20".join(city.split()), state)
	log.info("URL 	TO REQUEST: %s \n" % url)
	
	# Given the url, request the HTML page
	headers = { 'User-Agent' : user_agent }
	response = requests.get(url, headers=headers)
	html = response.text.encode('utf-8')
	
	# Save to file	
	with open(os.path.join(args.datadir, city + '-search-page.json'), "w") as h:
	 	h.write(html)

	# Parse json to get url
	js = json.loads(html)
	results = js['results']
	log.info("RESULTS: %s \n " % results[0])
	urls = results[0]['urls'][0]
	log.info("URLS: %s \n " % urls)

	# get tourism page url
	tourism_url = urls['url']
	log.info("TOURISM PAGE URL: %s \n" % tourism_url)
	return tourism_url

""" STEP 2  """
def get_city_page(tourism_url):
	""" 
		Get the URL of the hotels of the city
		using the URL returned by the function
		get_tourism_page()
	"""

	url = base_url + tourism_url

	# Given the url, request the HTML page
	headers = { 'User-Agent' : user_agent }
	response = requests.get(url, headers=headers)
	html = response.text.encode('utf-8')
	
	# Save to file	
	with open(os.path.join(args.datadir, args.city + '-tourism-page.html'), "w") as h:
	 	h.write(html)


	# Use BeautifulSoup to extract the url for the list of hotels in 
	# the city and state we are interested in.
	# For exampel in this case we need to  
	#<li class="hotels twoLines">
	#<a href="/Hotels-g60745-Boston_Massachusetts-Hotels.html" data-trk="hotels_nav"
	soup = BeautifulSoup(html)
	li = soup.find("li", {"class": "hotels twoLines"})
	city_url = li.find('a', href = True)
	log.info("CITY PAGE URL: %s" % city_url['href'])
	return city_url['href']


""" STEP 3 """
def get_hotellist_page(city_url, count):
	""" Get the hotel list page given the url returned by
		get_city_page(). Return the html after saving
		it to the datadir 
	"""

	url = base_url + city_url
	# Sleep 2 sec before starting a new http request
	time.sleep(2)
	# Request page
	headers = { 'User-Agent' : user_agent }
	response = requests.get(url, headers=headers)
	html = response.text.encode('utf-8')
	# Save the 
	with open(os.path.join(args.datadir, args.city + '-hotelist-' + str(count) + '.html'), "w") as h:
	 	h.write(html)
	return html
	

""" STEP 4 """
def parse_hotellist_page(html):
	""" Parse the html pages returned by get_hotellist_page().
		Return the next url page to scrape (a city can have
		more than one page of hotels) if there is, else exit
		the script.
	"""

	soup = BeautifulSoup(html)
# Extract hotel name, star rating and number of reviews
	hotel_boxes = soup.findAll('div', {'class' :'listing easyClear  p13n_imperfect '})
	for hotel_box in hotel_boxes:
		name = hotel_box.find('div', {'class' :'listing_title'}).find(text=True)
		try:
			rating = hotel_box.find('div', {'class' :'listing_rating'})
			reviews = rating.find('span', {'class' :'more'}).find(text=True)
			stars = hotel_box.find("img", {"class" : "sprite-ratings"})
		except Exception, e:
			log.error("No ratings for this hotel")
			reviews = "N/A"
			stars = 'N/A'

		if stars != 'N/A':
			#log.info("Stars: %s" % stars['alt'].split()[0])
			stars = stars['alt'].split()[0]
		log.info("HOTEL NAME: %s" % name)
		log.info("HOTEL REVIEWS: %s" % reviews)
		log.info("HOTEL STAR RATING: %s \n" % stars)

# # Get next URL page if exists, else exit
	div = soup.find("div", {"class" : "unified pagination standard_pagination"})
	# check if last page
	if div.find('span', {'class' : 'nav next ui_button disabled'}):
		log.info("We reached last page")
		sys.exit()
	# If it is not las page there must be the Next URL
	hrefs = div.findAll('a', href= True)
	for href in hrefs:
		if href.find(text = True) == 'Next':
			log.info("Next url is %s" % href['href'])
			return href['href']


	
if __name__ == "__main__":

	# Get current directory
	current_dir = os.getcwd()

	# Create datadir if does not exist
	if not os.path.exists(os.path.join(current_dir, args.datadir)):
		os.makedirs(os.path.join(current_dir, args.datadir))
    
    # Obtain the url of the toursim page 
	tourism_url = get_tourism_page(args.city, args.state)
	#Get URL to obtaint the list of hotels in a specific city
	city_url = get_city_page(tourism_url)
	c=0
	while(True):
		c +=1
		html = get_hotellist_page(city_url,c)
		city_url = parse_hotellist_page(html)

		
	