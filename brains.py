import config
import random
import urllib2
import json
import math
import countryinfo
from google.appengine.ext import db
import dbstructs


def getIndicatorValue(country, indicator):
	val = False
	response = urllib2.urlopen(config.configobject['wb_indicator_url'].format(country=country, indicator=indicator))
	data = json.loads(response.read())
	for year in data[1]:
		cand = year['value']
		if cand:
			try:
				val = math.ceil(float(cand))
			except:
				val = cand
			break;
	return val

def codeForCountry(country):
	for co in countryinfo.countries:
		if co['name'] == country:
			return co['code']

def makeVisLink(tweet):
	cos = ";".join([codeForCountry(x) for x in tweet.countries])
	url = config.configobject['vis_url'].format(country=cos, indicator=tweet.spec['relevant_data'][1])
	return url

def compose(tweet):
	template = random.choice(tweet.spec['response_templates'])
	value = getIndicatorValue(codeForCountry(tweet.countries[0]), tweet.spec['relevant_data'][1])
	if value:
		out = template.format(country=tweet.countries[0], value=value)
		if tweet.tags:
			out += ' ' + ' '.join(tweet.tags)
		out += ' ' + makeVisLink(tweet)
		return out
	else:
		return False #We can't make a tweet :-(


def parse(spec, tweets):
	for tweet in tweets:
		tweet.text = tweet.text.lower()
		tweet.words = set(tweet.text.split(' '))
		tweet.stemmedwords = tweet.words.union(set(word[:-1] for word in tweet.words if word.endswith('s'))) #a horrible hack instead of stemming
		tweet.tags = set(word for word in tweet.words if word.startswith('#'))
		tweet.users = set(word for word in tweet.words if word.startswith('@'))
		tweet.countries = [country[0] for country in config.configobject["countries"] if country[1].issubset(tweet.words)]	
		tweet.spec = spec

	return tweets

def select(tweets):
	outtweets = []
	for tweet in tweets:
		interesting = True

		# EXCLUSIONS FIRST!
		if not len(tweet.countries):
			continue

		for synonyms in tweet.spec["search_criteria"]:
			if not tweet.stemmedwords.intersection(synonyms): 
				interesting = False
				break
		key = db.Key.from_path('TweetParent', 'test', 'TweetDbEntry', str(tweet.id))
		if dbstructs.TweetDbEntry.get(key):
			continue #we've already responded or tried to respond to this tweet

		if interesting:
			dbstructs.TweetDbEntry(key_name = str(tweet.id), message = tweet.text, parent = dbstructs.parentkey).put()
			outtweets.append(tweet)
		else:
			print "rejected: ", tweet
	return outtweets


	

if __name__ == '__main__':
	testspec = 	{
		"twitter_search_term" : "trade",
		"search_criteria" : [["trade", "import"],["tariff", "embargo"]],
		"relevant_data" : [],
		"response_templates" : ["Import tarrifs in {country} are {value}", "There is a {value} level of import tax in {country}"],
		}

	class Tweet():
		def __init__(self, text):
			self.text = text

	tweets = [
		Tweet("embargo import tests tests testing #test @user united kingdom"),
		Tweet("could be @dpinsen bashing seems tendentious. an assertive trade policy can encourage investment no? e.g., reagan's japan tariff threats?"),
		Tweet("this shouldn't get through the #test"),
		Tweet("united arab emirates trade tariffs"),
		]
	for tweet in select(parse(testspec, tweets)):
		print "text: ", tweet.text
		print "words: ", tweet.words
		print "stemmedwords: ", tweet.stemmedwords
		print "tags: ", tweet.tags
		print "users: ", tweet.users
		print "countries: ", tweet.countries
		print

