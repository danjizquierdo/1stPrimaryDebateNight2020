# import pandas as pd
import numpy as np
# from pprint import pprint
from collections import defaultdict
from py2neo import Graph, Node, Relationship
import json

graph = Graph("bolt://localhost:7687", auth=("neo4j", "password")) 

# def get_timestamp(dt_ish):
#     if isinstance(dt_ish,str):
#         return pd.to_datetime(dt_ish).timestamp()
#     else:
#         return dt_ish.timestamp()

def dict_to_node(datadict,*labels,primarykey=None,primarylabel=None,):
    # if 'created_at' in datadict:
    #     datadict['timestamp']=get_timestamp(datadict['created_at'])
    cleandict={}
    for key,value in datadict.items():
        if isinstance(datadict[key],np.int64):
            cleandict[key] = int(datadict[key])
        elif key == 'extended_tweet':
            cleandict[key] = str(datadict['extended_tweet']['full_text'])
        elif not isinstance(datadict[key],(int,str,float)):
            cleandict[key] = str(datadict[key])
        else:
            cleandict[key] = datadict[key]

    node = Node(*labels,**cleandict)
    node.__primarylabel__= primarylabel or labels[0]
    node.__primarykey__= primarykey
    return node

def hashtags_to_nodes(ents):
    out= []
    if ents['hashtags']:
        for each in ents['hashtags']:
            out.append(dict_to_node(each,'Hashtag',primarykey='text',))
    return out

def mentions_to_nodes(ents):
    out=[]
    if ents['user_mentions']:
        for each in ents['user_mentions']:
            each.pop('indices')
            out.append(user_dtn(each))
    return out

# def urls_to_nodes(ents):
#     out=[]
#     if ents['urls']:
#         for each in ents['urls']:
#             each.pop('indices')
#             out.append(dict_to_node(each,'Url',primarykey='expanded_url',primarylabel='Url'))
#     return out

# def media_to_nodes(ents):
#     out= []
#     if ents['media']:
#         for each in ents['media']:
#             each.pop('indices')
#             out.append(dict_to_node(each,'Media',each['type'].title(),primarykey='id',primarylabel='Media'))
#     return out

def ent_parser(ents):
    output={}
    dents = defaultdict(int)
    dents.update(ents)
    output['hashtags']= hashtags_to_nodes(dents)
    output['mentions']= mentions_to_nodes(dents)
    # output['urls']= urls_to_nodes(dents)
    # output['media']= media_to_nodes(dents)
    return {k:v for (k,v) in output.items() if v}

def user_dtn(datadict):
#     if datadict['id'] in user_ids:
#         return dict_to_node(datadict,'Target',primarykey='id',primarylabel='User',)
    return dict_to_node(datadict,'User',primarykey='id',primarylabel='User')



def seperate_children(tweet):
    try:
        retweeted = tweet.pop('retweeted_status')
    except:
        retweeted = []
    try:
        quoted = tweet.pop('quoted_status')
    except:
        quoted = []

    output=defaultdict(int)
    try:
        output['user'] = tweet.pop('user')
    except:
        output['user']=[]
    try:
        output['ents'] = tweet.pop('entities')
    except:
        output['ents'] = []
    output['tweet'] = dict(tweet)

    if isinstance(retweeted,dict) and isinstance(quoted,dict):
        retweeted.pop('quoted_status')
        output['qtuser'] = quoted.pop('user')
        output['qents'] = quoted.pop('entities')

        output['rtuser'] =retweeted.pop('user')
        output['rents']=retweeted.pop('entities')
        output['retweeted'] = retweeted

        output['quoted'] = quoted

    elif isinstance(quoted,dict):
        output['qtuser'] = quoted.pop('user')
        output['qents'] = quoted.pop('entities')
        output['quoted'] = quoted


    elif isinstance(retweeted,dict):
        output['rtuser']= retweeted.pop('user')
        output['rents']= retweeted.pop('entities')
        output['retweeted']=retweeted

    return output

def push_tweet(tweetdict):
    tweetdict=json.loads(tweetdict)
    dicts=seperate_children(tweetdict)

    tx = graph.begin()
    if isinstance(dicts['user'],dict):
        user =  user_dtn(dicts['user'])
    else:
        try:
            gaffer = user_dtn(dicts['tweet']['delete']['status'])
            regret = dict_to_node(dicts['tweet']['delete']['status'],'Tweet')
            deleted = Relationship(gaffer,'DELETES',regret,timestamp=dicts['tweet']['delete']['timestamp_ms'])
            tx.merge(gaffer,primary_key='id')
            tx.merge(regret,primary_key='id')
            tx.merge(deleted)
            tx.commit()
            return
        except:
            print('Failed to find gaffer')
            return        
    tweet = dict_to_node(dicts['tweet'],'Tweet')

    # tx.merge(user,primary_key='id')


    if 'retweeted' in dicts.keys() and 'quoted' in dicts.keys():
        # tweet.add_label('Retweet')
        retweet = dict_to_node(dicts['retweeted'],'Tweet')
        quoted = dict_to_node(dicts['quoted'], 'Tweet')
        rtuser = user_dtn(dicts['rtuser'])
        qtuser = user_dtn(dicts['qtuser'])

        # tweeted = Relationship(user,'TWEETS', tweet, timestamp= tweet['timestamp'],
        #                        created_at = tweet['created_at'], usrStatusCount= user['statuses_count'],
        #                       usrFollowerCount= user['followers_count'], usrFavoritesCount = user['favourites_count'])

        tweeted = Relationship(user,'RETWEETS', retweet, timestamp= tweet['timestamp'],
                       created_at = tweet['created_at'], usrStatusCount= rtuser['statuses_count'],
                      usrFollowerCount= rtuser['followers_count'], usrFavoritesCount = rtuser['favourites_count'],replyCount= retweet['reply_count'])


        tweeted2 = Relationship(rtuser,'TWEETS', retweet,timestamp= retweet['timestamp'],
                                created_at = retweet['created_at'])

        tweeted3 = Relationship(qtuser,'TWEETS',quoted, timestamp= quoted['timestamp'],
                                created_at = quoted['created_at'])

        # retweeted = Relationship(tweet,'RETWEETS',retweet, timestamp= tweet['timestamp'], favcount=retweet['favorite_count'],
        #                          createdAt=tweet['created_at'],
        #                         replyCount= retweet['reply_count'], sourceFollowers = rtuser['followers_count'],
        #                         retweetCount=retweet['retweet_count'],quoteCount=retweet['quote_count'])

        quotes = Relationship(retweet,'QUOTES',quoted,timestamp= quoted['timestamp'],
                                favcount=quoted['favourites_count'],
                                replyCount= quoted['reply_count'], sourceFollowers = qtuser['followers_count'], createdAt= retweet['created_at'],
                                retweetCount=quoted['retweet_count'],quoteCount=quoted['quote_count'], usrStatusCount= qtuser['statuses_count'],
                              usrFollowerCount= qtuser['followers_count'], usrFavoritesCount = qtuser['favourites_count'])

        tx.merge(retweet,primary_key='id')
        tx.merge(user,primary_key='id')
        tx.merge(tweeted, primary_key='timestamp')


        tx.merge(rtuser,primary_key = 'id')
        tx.merge(retweet,primary_key='id')
        tx.merge(tweeted2)

        tx.merge(qtuser,primary_key='id')
        tx.merge(quoted,primary_key='id')
        # tx.merge(retweeted)
        tx.merge(tweeted3)
        tx.merge(quotes)

#         for ent,ls in ent_parser(dicts['rents']).items():
#             for each in ls:
#                 contains= Relationship(retweet,'CONTAINS',each)
#                 tx.merge(each,ent,primary_key=each.__primarykey__)
#                 tx.merge(contains)

        for ent,ls in ent_parser(dicts['qents']).items():
            if ls:
                for each in ls:

                    contains= Relationship(quoted,'CONTAINS',each)
                    tx.merge(each,ent, primary_key=each.__primarykey__)
                    tx.merge(contains)

        for ent,ls in ent_parser(dicts['rents']).items():
            if ls:
                for each in ls:
                    contains= Relationship(retweet,'CONTAINS',each)
                    tx.merge(each,ent,primary_key=each.__primarykey__)
                    tx.merge(contains)



    elif 'retweeted' in dicts.keys() and dicts['user']['verified']:
        tweet.add_label('Retweet')
        rtuser = user_dtn(dicts['rtuser'])
        retweet = dict_to_node(dicts['retweeted'],'Tweet')


        # tweeted = Relationship(user,'TWEETS',tweet, timestamp= tweet['timestamp'],
        #                        created_at = tweet['created_at'], usrStatusCount= user['statuses_count'],
        #                       usrFollowerCount= user['followers_count'], usrFavoritesCount = user['favourites_count'])

        tweeted = Relationship(user,'RETWEETS',rtuser, timestamp= tweet['timestamp'],
                               created_at = tweet['created_at'], usrStatusCount= rtuser['statuses_count'],
                              usrFollowerCount= rtuser['followers_count'], usrFavoritesCount = rtuser['favourites_count'],replyCount= retweet['reply_count'])


        tweeted2 = Relationship(rtuser,'TWEETS',retweet,timestamp= retweet['timestamp'],
                                created_at = retweet['created_at'])
#         retweeted = Relationship(tweet,'RETWEETS',retweet,timestamp= retweet['timestamp'],
#                                 created_at = retweet['created_at'])
        # retweeted = Relationship(tweet,'RETWEETS',retweet, timestamp= tweet['timestamp'], favcount=retweet['favourites_count'],
        #                         replyCount= retweet['reply_count'], sourceFollowers = rtuser['followers_count'], createdAt= tweet['created_at'],
        #                         retweetCount=retweet['retweet_count'],quoteCount=retweet['quote_count'])

        tx.merge(user,primary_key='id')
        tx.merge(rtuser,primary_key = 'id')
        tx.merge(tweeted)
        tx.merge(retweet,primary_key='id')
        tx.merge(tweeted2)

        for ent,ls in ent_parser(dicts['rents']).items():
            if ls:
                for each in ls:
                    contains= Relationship(retweet,'CONTAINS',each)
                    tx.merge(each,ent,primary_key=each.__primarykey__)
                    tx.merge(contains)



    elif 'quoted' in dicts.keys():
        # tweet.add_label('Qtweet')
        qtuser = user_dtn(dicts['qtuser'])
        quoted = dict_to_node(dicts['quoted'],'Tweet')

        tweeted = Relationship(user,'TWEETS',tweet, timestamp= tweet['timestamp'],
                               created_at = tweet['created_at'], usrStatusCount= user['statuses_count'],
                              usrFollowerCount= user['followers_count'], usrFavoritesCount = user['favourites_count'])

        tweeted2 = Relationship(qtuser,'TWEETS',quoted,timestamp= quoted['timestamp'],
                                created_at = quoted['created_at'])

        quotes = Relationship(tweet,'QUOTES',quoted, timestamp= tweet['timestamp'], favcount=quoted['favourites_count'],
                                replyCount= quoted['reply_count'], sourceFollowers = qtuser['followers_count'], createdAt= tweet['created_at'],
                                retweetCount=quoted['retweet_count'],quoteCount=quoted['quote_count'], usrStatusCount= qtuser['statuses_count'],
                              usrFollowerCount= qtuser['followers_count'], usrFavoritesCount = qtuser['favourites_count'])

        tx.merge(tweet,primary_key='id')
        tx.merge(user,primary_key='id')
        tx.merge(tweeted)
        tx.merge(qtuser,primary_key='id')
        tx.merge(quoted,primary_key='id')
        tx.merge(tweeted2)
        tx.merge(quotes)

        for ent,ls in ent_parser(dicts['ents']).items():
            if ls:
                for each in ls:
                    contains= Relationship(tweet,'CONTAINS',each)
                    tx.merge(each,ent,primary_key=each.__primarykey__)
                    tx.merge(contains)

        for ent,ls in ent_parser(dicts['qents']).items():
            if ls:
                for each in ls:
                    contains= Relationship(quoted,'CONTAINS',each)
                    tx.merge(each,ent,primary_key=each.__primarykey__)
                    tx.merge(contains)


#     subg = tweeted

    else:
        tweeted = Relationship(user,'TWEETS',tweet, timestamp= tweet['timestamp'],
                               created_at = tweet['created_at'], usrStatusCount= user['statuses_count'],
                              usrFollowerCount= user['followers_count'], usrFavoritesCount = user['favourites_count'])
        tx.merge(tweet,primary_key='id')
        tx.merge(user,primary_key='id')
        tx.merge(tweeted)
        for ent,ls in ent_parser(dicts['ents']).items():
            if ls:
                for each in ls:
                    contains= Relationship(tweet,'CONTAINS',each)
        #             subg = subg | contains
                    tx.merge(each,str(ent),primary_key=each.__primarykey__)
                    tx.merge(contains)

    tx.commit()