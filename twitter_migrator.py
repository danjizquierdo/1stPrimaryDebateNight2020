from tweepy import Stream
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from graphstream import *
import time

import credentials

class TwitterStreamer():

	def stream_tweets(self,tag_list,user_list):

		listener = StdOutListener()
		auth = OAuthHandler(credentials.CONSUMER_KEY,credentials.CONSUMER_SECRET)
		auth.set_access_token(credentials.ACCESS_TOKEN,credentials.ACCESS_TOKEN_SECRET)

		stream = Stream(auth,listener)
		start = time.time()
		try:
			stream.filter(track=tag_list,follow=user_list)
		except BaseException as e:
			print(f'Error on stream after {time.time()-start} seconds: {e}')
			time.sleep(3)
			print('Still listening . . .')
			self.stream_tweets(tag_list,user_list)

class StdOutListener(StreamListener):

	# def __init__(self,tag_list,user_list):
	# 	self.tag_list=tag_list
	# 	self.user_list=user_list
	def on_data(self,data):
		try:
			push_tweet(data)
			return True
		except BaseException as e:
			print(f'Error on_data: {e}')
			return True
	def on_error(self,status):
		print(status)

if __name__ == '__main__':

	# tag_list = ['Joe Biden','Bernie Sanders','Kamala Harris', 'Cory Booker',
	# 'Elizabeth Warren',"Beto O'Rourke","Beto ORourke",
	# 'Amy Klobuchar','John Hickenlooper','Kirsten Gillibrand',
	# 'Andrew Yang','Julian Castro','Julián Castro','Eric Swalwell','Tulsi Gabbard',
	# 'Jay Inslee','Pete Buttigieg', 'John Delaney','Mike Gravel','Wayne Messam',
	# 'Tim Ryan','Marianne Willamson','Mayor Pete','Uncle Joe',
	# 'Bill de Blasio','de Blasio', 'deblasio', 'Seth Moulton', 'Steve Bullock',
	# 'Michael Bennet']
	# tag_list += ['@JoeBiden','@BernieSanders','@KamalaHarris','@CoryBooker',
	# '@ewarren','@BetoORourke','@amyklobuchar',
	# '@Hickenlooper','@SenGillibrand','@AndrewYang','@JulianCastro',
	# '@ericswalwell','@TulsiGabbard','@JayInslee','@PeteButtigieg','@JohnDelaney',
	# '@MikeGravel','@WayneMessam','@TimRyan','@marwilliamson','@GovBillWeld',
	# '@BilldeBlasio','@sethmoulton','@GovernorBullock','@MichaelBennet']
	tag_list = ['#debate','#election2020','#DemocraticDebate']
	user_ids = ['939091','216776631','30354991','15808765','357606935','342863309',
	'33537967','117839957','72198806','2228878592','19682187','377609596',
	'26637348','21789463','226222147','426028646','14709326','33954145',
	'466532637','21522338','476193064','248495200',
	'111721601','46545232']
	# filename = 'tweets_3.json'

	streamer = TwitterStreamer()
	streamer.stream_tweets(tag_list,user_ids)