import spacy
import numpy as np
from spacy.tokens import Doc
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import re
import pdb
import time
import pdb
from py2neo import Graph

nltk.download('vader_lexicon')
nlp = spacy.load("en_core_web_lg")
sentiment_analyzer = SentimentIntensityAnalyzer()

graph = Graph("bolt://localhost:7687", auth=("neo4j", "password")) 


def strip_tweets(tweet):
    '''Process tweet text to remove retweets, mentions,links and hashtags.'''
    retweet = r'RT:? ?@\w+:?'
    tweet= re.sub(retweet,'',tweet)
    mention = r'@\w+'
    tweet= re.sub(mention,'',tweet)
    links = r'^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$'
    tweet= re.sub(links,'',tweet)
    tweet_links = r'https:\/\/t\.co\/\w+|http:\/\/t\.co\/\w+'
    tweet=re.sub(tweet_links,'',tweet)  
    tweet_link = r'http\S+'
    tweet=re.sub(tweet_link,'',tweet)
    hashtag = r'#\w+'
    tweet= re.sub(hashtag,'',tweet)
    return tweet

def polarity_scores(doc):
    return sentiment_analyzer.polarity_scores(doc.text)

def graph_sentiment(text):
    tweet = nlp(strip_tweets(text))
    return tweet._.polarity_scores['compound'],tweet.vector


Doc.set_extension('polarity_scores', getter=polarity_scores)

def encode_sentiment(tweet):
    if tweet['truncated']:
    	if isinstance(tweet['extended_tweet'],str):
        	sentiment,embedding = graph_sentiment(tweet['extended_tweet'])
    	else:
    		return
    else:
    	if isinstance(tweet['text'],str):
        	sentiment,embedding = graph_sentiment(tweet['text'])
    	else:
    		return
    sentiment=float(sentiment)
    embedding = np.array2string(embedding,separator=',')
    t_id=tweet['id_str']
    query = '''MERGE (t:Tweet {id_str: $id})
    ON CREATE SET t.stranded = 1 
    ON MATCH SET t.sentiment = $sentiment,
        t.embedding = $embedding
    '''
    graph.run(query,id=t_id,sentiment=str(sentiment),embedding=embedding)

if __name__ == '__main__':
	query = '''MATCH (t:Tweet)
	WHERE NOT exists(t.sentiment)
	RETURN t
	'''
	tweets = graph.run(query)
	for tweet in tweets:
		encode_sentiment(tweet['t'])


