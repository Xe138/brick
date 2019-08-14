# Get Cat Fact from Twitter
# Set key - 'catfact_source' to change the twitter source
# Version 1.0.0
import re

def main(bag, config):

    if 'catfact_source' in config.keys():
        source = config['catfact_source']
    else:
        source = 'catfacts101'

    if bag['addressed'] and re.match('cat\s*fact', bag['msg'], re.I):
        return { 'call' : 'twitter', 'username' : source }

def recall(bag, config, tweets):
    tweets = tweets['result']
    
    posts = []
    for tweet in tweets:

        response = tweet['text']

        # Remove Hashtags
        for tag in reversed(tweet['entities']['hashtags']):
            response = (response[:tag['indices'][0]] + response[tag['indices'][1]:]).strip()

        # Remove User Mentions
        for tag in reversed(tweet['entities']['user_mentions']):
            response = (response[:tag['indices'][0]] + response[tag['indices'][1]:]).strip()

        posts.append(response)

    return posts