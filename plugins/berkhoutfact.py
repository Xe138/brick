# Get Berkhout Fact from Twitter
# Substitutes Captain Berkhout for Chuck Norris
# Set key - 'berkhoutfact_source' to change the twitter source
# Version 1.0.0
import re

def main(bag, config):

    if 'berkhoutfact_source' in config.keys():
        source = config['berkhoutfact_source']
    else:
        source = 'CNorrisLegend'

    if bag['addressed'] and re.match('(?:captain|cpt|capt)?\s*berkhout\s*fact', bag['msg'], re.I):
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

        # Substitute text
        response = re.sub('chuck norris', 'Captain Berkhout', response, 0, re.I)
        response = re.sub('chuck norris\'s?', 'Captain Berkhout\'s', response, 0, re.I)
        response = re.sub('chuck|norris', 'Berkhout', response, 0, re.I)
        response = re.sub('OMCN', 'OMCB', response)

        # Verify berkhout reference
        if re.search('berkhout', response, re.I) != None:
            posts.append(response)

    return posts