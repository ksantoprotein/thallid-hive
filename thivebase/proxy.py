# -*- coding: utf-8 -*-

import json
from pprint import pprint
from time import sleep, time
from random import randint, choice

from requests import Session

##### ##### storage ##### #####

url = 'https://ya.ru/'
timer = 10	# aka 10 sec

##### ##### ##### ##### #####

class Http():

	http = Session()
	proxies = None

	
class Proxy(Http):

	url_check = url

	files = {"state_proxy": 'proxy.json',}
			
	timestamp = {
				"upload": 60 * 60 * 1,		# 1 часа (обновление прокси)
				"uploader": 60 * 60 * 2,	# 2 часа (обновление прокси если другой не обновил)
				"check_proxy": timer,		# (время сканирование прокси)
				}
	protocol = 'https'	
	
	def __init__(self):
		self.state = {"http": [], "timestamp": int(time()), "upload": False}
		self.load_proxies()
		
	def load_proxies(self):
		try:
			with open(self.files["state_proxy"], 'r', encoding='utf8') as f:
				self.state = json.load(f)
			if not self.check_upload(): self.prepare_proxies()
			print('load proxies ok')
		except:	# not exist or bad file, load proxies
			self.prepare_proxies()
		
	def get_http(self):
		if not self.check_upload(): self.load_proxies()
		try:
			proxy = choice(self.state["http"])
		except:
			proxy = None
		return proxy
			
	def check_upload(self):
		dt = (int(time()) - self.state["timestamp"])
		load, upload, uploader = self.state["upload"], self.timestamp["upload"], self.timestamp["uploader"]
		if load and (dt > uploader): return False		# Если не произошло обновление прокси иным модулем
		if not load and (dt > upload): return False		# Если вышло время
		return True

	##### ##### kernel ##### #####
		
	def prepare_proxies(self):
	
		print('genesis new proxies')
		start = time()
		
		self.state["upload"], self.state["uploader"] = True, int(time())
		self.save_state()
		
		response = self.http.get('http://spys.me/proxy.txt')
		if response.ok:
			self.state["http"] = []
			for line in response.text.split('\n'):
				if line[:1] in '0123456789' and len(line) > 0:
					ip = line.split()[0]
					proxy = {self.protocol: ip}		# https	### proxy = {"http": ip, "https": ip}
					try:
						response = self.http.get(self.url_check, proxies=proxy, timeout=1)
						if response.ok:				
							self.state["http"].append(proxy)
							#print('ok', ip)
							if (time() - start) > self.timestamp["check_proxy"]: break
						else:
							print('sorry', ip)
					except:
						pass
						#print('ERROR', ip)
	
			self.state["upload"], self.state["timestamp"] = False, int(time())
			self.save_state()
			print(len(self.state["http"]), 'new proxies ok', round((time() - start), 0), 'sec')
			
		
	def save_state(self):
		with open(self.files["state_proxy"], 'w', encoding='utf8') as f:
			json.dump(self.state, f, ensure_ascii=False)
	
	##### ##### ##### ##### #####
	
#----- main -----
if __name__ == '__main__':
	
	proxies = Proxy()