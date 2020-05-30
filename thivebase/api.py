# -*- coding: utf-8 -*-

from pprint import pprint
import json
import math
import hashlib

from .rpc_client import RpcClient
from .broadcast import Tx
from .key import Key
from .storage import time_format, asset_precision, nodes, chain_id, prefix

from datetime import datetime, timedelta
from time import sleep, time
from random import randint, choice


class Account():

	"""
	name, RC, HIVE, HBD, HP
	"""

	def __init__(self):
		self.b4 = Api(report=True)
		
	def upload(self, login):
	
		self.name = login
		self.RC = self.b4.find_rc_account(self.name)
		
		tx = self.b4.get_account(self.name)
		
		self.HIVE = float(tx["balance"].split()[0])
		self.HBD = float(tx["sbd_balance"].split()[0])
		self.VEST = float(tx["vesting_balance"].split()[0])		# =0.000
		
		vests = float(str(tx["vesting_shares"]).split()[0])
		delegated = float(str(tx["delegated_vesting_shares"]).split()[0])
		received = float(str(tx["received_vesting_shares"]).split()[0])
		self.HP = self.b4.convert_vests_to_hive(vests + received - delegated)
		

class Api():

	app = 'thallid'

	def __init__(self, **kwargs):

		# Пользуемся своими нодами или новыми
		report = kwargs.pop("report", False)
		self.rpc = RpcClient(nodes=kwargs.pop("nodes", nodes), report=report)

		#chain_config = self.get_config()
		self.chain_id = chain_id	#chain_config["HIVE_CHAIN_ID"]
		self.prefix = prefix		#chain_config["HIVE_ADDRESS_PREFIX"]
		
		self.chain_properties = self.get_chain_properties()
		self.account_creation_fee = self.chain_properties["account_creation_fee"]
		
		self.asset_precision = asset_precision
		
		self.broadcast = Tx(self.rpc)
		self.finalizeOp = self.broadcast.finalizeOp
		
		self.key = Key(self.prefix)
		
		#self.resolve_url = resolve_url
		#self.rus_d = rus_d
		
	##### ##### condenser_api ##### #####
	
	def get_account_count(self):			# Возвращает количество зарегестрированных пользователей
		return(int( self.rpc.call('get_account_count') ))
		
	#get_account_history
	#get_account_references
	
	def get_block(self, n):
		return(self.rpc.call('get_block', int(n)))

	#get_block_header
	#get_blog
	
	def get_chain_properties(self):
		return(self.rpc.call('get_chain_properties'))
		
	def get_config(self):
		return(self.rpc.call('get_config'))
		
	#get_content
	
	def get_key_references(self, public_key):
		res = self.rpc.call('get_key_references', [public_key])
		if res: return res[0]
		return False

	def get_ops_in_block(self, n, ops=False):
		return(self.rpc.call('get_ops_in_block', int(n), ops))
		
	def get_transaction(self, trx_id):							# ?
		return(self.rpc.call('get_transaction', trx_id))
		
	def get_transaction_hex(self, trx_raw):						# ?
		return(self.rpc.call('get_transaction_hex', trx_raw))
		
	def get_witness_schedule(self):
		return(self.rpc.call('get_witness_schedule'))
		
	##### ##### Account ##### #####
		
	def get_accounts(self, accounts):
		return(self.rpc.call('get_accounts', accounts))

	def get_account(self, account):
		return(self.rpc.call('get_accounts', [account])[0])		### может быть ошибка если нет аккаунта
		
	def find_rc_account(self, account):
		info = self.rpc.call('find_rc_accounts', params={"accounts": [account]}, method='rc_api.')
		if info:
			rc = info["rc_accounts"][0]
			max_rc = int(rc["max_rc"])
			current_mana = int(rc["rc_manabar"]["current_mana"])
			last_update_time = rc["rc_manabar"]["last_update_time"]
			
			app = (int(time()) - last_update_time) * max_rc / (3 * 24 * 60 * 60)
			
			mana = (current_mana + app) if (current_mana + app) < max_rc else max_rc
			
			pct = int(100 * mana / max_rc)
			return pct
		
		return False
		
	##### ##### get_dynamic_global_properties ##### ##### 
		
	def get_dynamic_global_properties(self):

		# Returns the global properties
		for n in range(3):
			prop = self.rpc.call('get_dynamic_global_properties')
			if not isinstance(prop, bool):
			
				for p in ["head_block_number", "last_irreversible_block_num"]:
					value = prop.pop(p)
					prop[p] = int(value)
					
				# Obtain HIVE/VESTS ratio
				for p in ["total_vesting_fund_steem", "total_vesting_shares"]:
					value = prop.pop(p)
					prop[p] = float(value.split()[0])
						
				prop["now"] = datetime.strptime(prop["time"], time_format)
				prop["hive_per_vests"] = prop["total_vesting_fund_steem"] / prop["total_vesting_shares"]
				
				return prop
			sleep(3)
			
		return False
		
	def get_irreversible_block(self):
		info = self.get_dynamic_global_properties()
		if info:
			return(info["last_irreversible_block_num"])
		return False

	def get_head_block(self):
		info = self.get_dynamic_global_properties()
		if info:
			return(info["head_block_number"])
		return False
		
	def convert_hive_to_vests(self, amount):
		info = self.get_dynamic_global_properties()
		if info:
			asset = 'VESTS'
			vests = round(float(amount) / info["hive_per_vests"], self.asset_precision[asset])
			return vests
		return False

	def convert_vests_to_hive(self, amount):
		info = self.get_dynamic_global_properties()
		if info:
			asset = 'HIVE'
			vests = round(float(amount) * info["hive_per_vests"], self.asset_precision[asset])
			return vests
		return False
	
	##### ##### ##### ##### #####

	def check_login(self, login):

		if len(login) > 16:	## скорректировать под параметр блокчейна в инициализации
			return False
		if login[0] not in list('abcdefghijklmnopqrstuvwxyz'):
			return False
		for l in list(login[1:]):
			if l not in list('abcdefghijklmnopqrstuvwxyz0123456789.-'):
				return False
			
		return True

		
	def is_login(self, login):

		#Проверка существования логина
		account = self.rpc.call('get_accounts', [login])
		#account = self.get_accounts([login])
		if account:
			public_key = account[0]["memo_key"]
			return(public_key)
			
		return False
		
		
	def is_posting_key(self, login, public_key):
		account = self.rpc.call('get_accounts', [login])
		if account:
			keys = [key for key, auth in account[0]["posting"]["key_auths"]]
			if public_key in keys:
				return True
		return False
		
	##### ##### BROADCAST ##### #####
		
	def transfer(self, to, amount, asset, from_account, wif, **kwargs):

		# to, amount, asset, from_account, [memo]
		memo = kwargs.pop('memo', '')

		ops = []
		op = {
			"from": from_account,
			"to": to,
			"amount": '{:.{precision}f} {asset}'.format(float(amount), precision=self.asset_precision[asset], asset=asset),
			"memo": memo,
			}
		ops.append(['transfer', op])
		tx = self.finalizeOp(ops, wif)
		return tx
		
	

	##### ##### ##### ##### #####


	'''
	def vote(self, url, weight, voters, wif):
	
		#weight = -10000..10000
		#voters = list

		author, permlink = self.resolve_url(url)
		if not permlink:
			print('error url')
			return False
			
		ops = []
		for voter in voters:
			v = {
				"voter": voter,
				"author": author,
				"permlink": permlink,
				"weight": int(weight)
				}
			ops.append(['vote', v])
			
		tx = self.finalizeOp(ops, wif)
		return tx
		
		

		
	def transfers(self, raw_ops, from_account, wif):

		# to, amount, asset, memo

		ops = []
		for op in raw_ops:
			to, amount, asset, memo = op
			t = {
				"from": from_account,
				"to": to,
				"amount": '{:.{precision}f} {asset}'.format(
							float(amount),
							precision = self.asset_precision[asset],
							asset = asset
							),
				"memo": memo
				}
			ops.append(['transfer', t])
		
		tx = self.finalizeOp(ops, wif)
		return tx


	def transfer_to_vesting(self, to, amount, from_account, wif, **kwargs):

		# to, amount, from_account
		asset = 'GOLOS'

		ops = []
		tv = {
			"from": from_account,
			"to": to,
			"amount": '{:.{precision}f} {asset}'.format(
						float(amount),
						precision = self.asset_precision[asset],
						asset = asset
						),
			}
		ops.append(['transfer_to_vesting', tv])
		tx = self.finalizeOp(ops, wif)
		return tx


	def delegate_vesting_shares(self, delegatee, amount, delegator, wif, **kwargs):

		# делегируется не менее 0.010 GOLOS которые нужно перевести в GEST)
		vesting_shares = self.convert_golos_to_vests(amount)
		asset = 'GESTS'

		ops = []
		dvs = {
			"delegator": delegator,
			"delegatee": delegatee,
			"vesting_shares": '{:.{precision}f} {asset}'.format(
								vesting_shares,
								precision = self.asset_precision[asset],
								asset = asset
								),
			}
		ops.append(['delegate_vesting_shares', dvs])
		tx = self.finalizeOp(ops, wif)
		return tx
		
		
	def account_metadata(self, json_metadata, account, wif):
	
		ops = []
		jm = {
			"account": account,
			"json_metadata": json.dumps(json_metadata)
			}
		ops.append(['account_metadata', jm])

		tx = self.finalizeOp(ops, wif)
		return tx
		
		
	def follow(self, wtf, followings, followers, wif, **kwargs):
	
		# wtf = True (подписаться), False (отписаться), ignore - заблокировать
		# following - [] на кого подписывается
		# follower - [] кто подписывается
		
		if wtf == True and wtf != 'ignore':
			what = ['blog']						# подписаться
		elif wtf == 'ignore':
			what = ['ignore']					# заблокировать
		else:
			what = []							# отписаться

		ops = []
		for follower in followers:
			for following in followings:
			
				if follower != following:
					json_body = [
						'follow', {
							"follower": follower,
							"following": following,
							"what": what
							}
						]
				
					f = {
						"required_auths": [],
						"required_posting_auths": [follower],
						"id": 'follow',
						"json": json.dumps(json_body)
						}
					ops.append(['custom_json', f])

		tx = self.finalizeOp(ops, wif)
		return tx

		
	def post(self, title, body, author, wif, **kwargs):
	
		"""
		category = ''
		url = ''
		permlink = ''
		tags = []
		
		beneficiaries = 'login:10000'
		weight = 10000
		curation = max or int 5100..9000
		"""
	
		asset = 'GBG'
		
		parent_beneficiaries = 'thallid'
		category = kwargs.pop("category", parent_beneficiaries)
		app = kwargs.pop("app", parent_beneficiaries)
		beneficiaries = kwargs.pop("beneficiaries", False)
		
		if beneficiaries:
			a, w = beneficiaries.split(':')
			beneficiaries = [{"account": a, "weight": int(w)}]
		
		curation = kwargs.pop("curation", False)
		if curation == 'max':
			cur = self.get_curation_percent()
			if cur:
				curation = cur["max"]
			else:
				return False
		else:
			try:
				curation = int(curation)
			except:
				curation = False

		url = kwargs.pop("url", None)
		if url:
			parent_author, parent_permlink = self.resolve_url(url)			# comment
		else:
			parent_author, parent_permlink = '', category					# post
		
		permlink = kwargs.pop("permlink", None)
		if not permlink:
			# подготовить пермлинк самостоятельно
			permlink = ''.join([self.rus_d.get(s, s) for s in title.lower()]) + '-' + str( round(time()) )

		tags = kwargs.pop("tags", ['golos'])
		json_metadata = {"app": app, "tags": tags}
		
		max_accepted_payout = kwargs.pop("max_accepted_payout", 10000)
		allow_votes = kwargs.pop("allow_votes", True)
		allow_curation_rewards = kwargs.pop("allow_curation_rewards", True)
	
		ops = []
		c = {
				"parent_author": parent_author,
				"parent_permlink": parent_permlink,
				"author": author,
				"permlink": permlink,
				"title": title,
				"body": body,
				"json_metadata": json.dumps(json_metadata),
			}
		ops.append(['comment', c])
		
		extensions = []
		if beneficiaries:
			extensions.append([0, {"beneficiaries": beneficiaries}])
		if curation:
			extensions.append([2, {"percent": curation}])
		
		co = {
				"author": author,
				"permlink": permlink,
				"max_accepted_payout": '{:.{precision}f} {asset}'.format(
									float(max_accepted_payout),
									precision = self.asset_precision[asset],
									asset = asset
									),
				"percent_steem_dollars": 10000,
				"allow_votes": allow_votes,
				"allow_curation_rewards": allow_curation_rewards,
				"extensions": extensions
			}
		ops.append(['comment_options', co])

		tx = self.finalizeOp(ops, wif)
		return tx


	def replace(self, title, body, author, wif, **kwargs):
	
		parent_beneficiaries = 'thallid'
		category = kwargs.pop("category", parent_beneficiaries)

		url = kwargs.pop("url", None)
		if url:
			parent_author, parent_permlink = self.resolve_url(url)			# comment
		else:
			parent_author, parent_permlink = '', category					# post
		
		permlink = kwargs.pop("permlink", None)
		if not permlink:
			print('not permlink')
			return False

		app = kwargs.pop("app", parent_beneficiaries)
		tags = kwargs.pop("tags", ['golos'])
		json_metadata = {"app": app, "tags": tags}
	
		ops = []
		c = {
				"parent_author": parent_author,
				"parent_permlink": parent_permlink,
				"author": author,
				"permlink": permlink,
				"title": title,
				"body": body,
				"json_metadata": json.dumps(json_metadata),
			}
		ops.append(['comment', c])
		
		tx = self.finalizeOp(ops, wif)
		return tx

		
		

		
	def withdraw_vesting(self, amount, account, wif, **kwargs):

		# amount, account
		# понижается не менее 10х fee (сейчас 10 GOLOS которые нужно перевести в GEST)
		vesting_shares = self.convert_golos_to_vests(amount)
		asset = 'GESTS'

		ops = []
		wv = {
			"account": account,
			"vesting_shares": '{:.{precision}f} {asset}'.format(
								vesting_shares,
								precision = self.asset_precision[asset],
								asset = asset
								),
			}
		ops.append(['withdraw_vesting', wv])
		tx = self.finalizeOp(ops, wif)
		return tx

		
	def account_create(self, login, password, creator, wif, **kwargs):

		create_with_delegation = False	###

		# login = account name must be at most 16 chars long, check if account already exists
		# roles = ["posting", "active", "memo", "owner"]
		paroles = self.key.get_keys(login, password)

		fee = self.account_creation_fee
		json_metadata = kwargs.pop("json_metadata", [])	###
			
		owner_key_authority = [ [paroles["public"]["owner"], 1] ]
		active_key_authority = [ [paroles["public"]["active"], 1] ]
		posting_key_authority = [ [paroles["public"]["posting"], 1] ]
		memo = paroles["public"]["memo"]
		
		owner_accounts_authority = []
		active_accounts_authority = [ [creator, 1] ]
		posting_accounts_authority = [ [creator, 1] ]
		#active_accounts_authority = []
		#posting_accounts_authority = []
		
		ops = []
		ca = {
			'fee': fee,
			'creator': creator,
			'new_account_name': login,
			'owner': {
				'weight_threshold': 1,
				'account_auths': owner_accounts_authority,
				'key_auths': owner_key_authority,
			},
			'active': {
				'weight_threshold': 1,
				'account_auths': active_accounts_authority,
				'key_auths': active_key_authority,
			},
			'posting': {
				'weight_threshold': 1,
				'account_auths': posting_accounts_authority,
				'key_auths': posting_key_authority,
			},
			'memo_key': memo,
			'json_metadata': json.dumps(json_metadata),
		}

		#if create_with_delegation:
		#	required_fee_vests = 0
		#	s["delegation"] = '%s GESTS' % required_fee_vests
		#	op = operations.AccountCreateWithDelegation(**s)
		#else:
		#	op = operations.AccountCreate(**s)
			
		ops.append(['account_create', ca])
		tx = self.finalizeOp(ops, wif)
		return tx
			

	def account_witness_proxy(self, account, proxy, wif):
	
		ops = []
		awp = {
			"account": account,
			"proxy": proxy,
			}
		ops.append(['account_witness_proxy', awp])
		tx = self.finalizeOp(ops, wif)
		return tx
		
	
	def repost(self, url, account, wif, **kwargs):	###
	
		#title = kwargs.pop("title", None)	
		#body = kwargs.pop("body", None)		
		#['title', 'body', 'json_metadata']
	
		author, permlink = resolve_url(url)
		ops = []
		json_body = [
			'reblog', {
				"account": account,
				"author": author,
				"permlink": permlink
				}
			]
	
		f = {
			"required_auths": [],
			"required_posting_auths": [account],
			"id": 'follow',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', f])

		tx = self.finalizeOp(ops, wif)
		return tx
		
	

	'''	
		
#############################

	'''
	def get_curation_percent(self):
		tx = self.rpc.call('get_witness_schedule')
		try:
			min = int(tx["median_props"]["min_curation_percent"])
			max = int(tx["median_props"]["max_curation_percent"])
			return({"min": min, "max": max})
		except:
			return False
			
		
	
	def account_update(self, new_password, account, old_password, **kwargs):

		create_with_delegation = False	###

		# login = account name must be at most 16 chars long, check if account already exists
		# roles = ["posting", "active", "memo", "owner"]
		old_paroles = self.key.get_keys(account, old_password)
		new_paroles = self.key.get_keys(account, new_password)

		json_metadata = kwargs.pop("json_metadata", {})	###
			
		owner_key_authority = [ [new_paroles["public"]["owner"], 1] ]
		active_key_authority = [ [new_paroles["public"]["active"], 1] ]
		posting_key_authority = [ [new_paroles["public"]["posting"], 1] ]
		memo = new_paroles["public"]["memo"]
		
		owner_accounts_authority = []
		#active_accounts_authority = [ [creator, 1] ]
		#posting_accounts_authority = [ [creator, 1] ]
		active_accounts_authority = []
		posting_accounts_authority = []
		
		ops = []
		au = {
			'account': account,
			'owner': {
				'weight_threshold': 1,
				'account_auths': owner_accounts_authority,
				'key_auths': owner_key_authority,
			},
			'active': {
				'weight_threshold': 1,
				'account_auths': active_accounts_authority,
				'key_auths': active_key_authority,
			},
			'posting': {
				'weight_threshold': 1,
				'account_auths': posting_accounts_authority,
				'key_auths': posting_key_authority,
			},
			'memo_key': memo,
			'json_metadata': json.dumps(json_metadata),
		}

			
		ops.append(['account_update', au])
		tx = self.finalizeOp(ops, old_paroles["private"]["owner"])
		return tx
		
	def get_median_price(self):

		# Фид-прайс делегатов
		feed = self.rpc.call('get_feed_history')	# HF-18
		base = float(feed["current_median_history"]["base"].split()[0])
		quote = float(feed["current_median_history"]["quote"].split()[0])

		return(round(base / quote, self.asset_precision["GBG"]))
		

	def get_order_price(self):

		# усредненный прайс на внутренней бирже
		limit = 1
		feed = self.rpc.call('get_order_book', limit)
		ask = float(feed["asks"][0]["price"])
		bid = float(feed["bids"][0]["price"])

		return(round( (ask + bid) / 2, self.asset_precision["GBG"]))

		
	def get_all_accounts(self):
	
		n = self.get_account_count()
		limit = 1000
		print('find', n, 'accounts')
		
		accounts_dict = {}
		start_login = 'a'
		while True:
			print(start_login)
			logins = self.rpc.call('lookup_accounts', start_login, limit)
			
			if len(logins) == 1 and logins[0] == start_login:
				accounts = self.get_accounts(logins)
				for account in accounts:
					accounts_dict[account["name"]] = account
				break

			accounts = self.get_accounts(logins[:-1])
			for account in accounts:
				accounts_dict[account["name"]] = account

			start_login = logins[-1:][0]
	
		return accounts_dict

		
	def get_follow(self, account):
	
		follow = {"follower": [], "following": []}
		account_follow = self.rpc.call('get_follow_count', account)
		
		#account_follow["follower_count"]
		#account_follow["following_count"]
		
		start_follower = 'a'
		while True:
			tx = self.rpc.call('get_followers', account, start_follower, 'blog', 1000)
			
			if len(tx) == 1 and tx[0]["follower"] == start_follower:
				follow["follower"].append(start_follower)
				break

			for line in tx[:-1]:
				follow["follower"].append(line["follower"])
			start_follower = tx[-1:][0]["follower"]
			
		start_follower = 'a'
		while True:
			tx = self.rpc.call('get_following', account, start_follower, 'blog', 100)
			
			if len(tx) == 1 and tx[0]["following"] == start_follower:
				follow["following"].append(start_follower)
				break

			for line in tx[:-1]:
				follow["following"].append(line["following"])
			start_follower = tx[-1:][0]["following"]

		account_follow["follower"] = follow["follower"]
		account_follow["following"] = follow["following"]

		return account_follow

		

	def get_account_reputations(self, account):
	
		# Определяем репутацию аккаунта
		reputations = self.rpc.call('get_account_reputations', [account])
		rep = int(reputations[0]["reputation"])
		if rep == 0:
			reputation = 25
		else:
			score = (math.log10(abs(rep)) - 9) * 9 + 25
			if rep < 0:
				score = 50 - score
			reputation = round(score, 3)
			
		return(reputation)
		
	def get_ticker(self):
		ticker = self.rpc.call('get_ticker')
		try:
			t = {"bid": round(float(ticker["highest_bid"]), 6), "ask": round(float(ticker["lowest_ask"]), 6)}
		except:
			return False
		
		return(t)

		
	def get_tickers(self):
		ticker = self.rpc.call('get_ticker')
		try:
			bid = float(ticker["highest_bid"])
			ask = float(ticker["lowest_ask"])
			
			t = {"GOLOS_GBG": {"bid": bid, "ask": ask}, "GBG_GOLOS": {"bid": 1 / ask, "ask": 1 / bid} }
		except:
			return False
		
		return(t)
	
		
	'''	
	
	
##### ##### SteemMonsters ##### #####
	
class SteemMonsters(Api):

	app = 'thallid'

	def __init__(self, **kwargs):

		# Пользуемся своими нодами или новыми
		report = kwargs.pop("report", False)
		self.rpc = RpcClient(nodes=kwargs.pop("nodes", nodes), report=report)

		self.broadcast = Tx(self.rpc)
		self.finalizeOp = self.broadcast.finalizeOp
		
		self.prefix = prefix		
		self.key = Key(self.prefix)
		
		
	def sm_token_transfer(self, to, amount, from_account, wif, asset = 'DEC', active = False):
	
		sign_active = [from_account] if active else []
		sign_posting = [] if active else [from_account]

		ops = []
		json_body = {
						"to": to,
						"qty": str(amount),
						"token": asset,
						"type": 'withdraw',
						"app": self.app,
					}
	
		op = {
			"required_auths": sign_active,
			"required_posting_auths": sign_posting,
			"id": 'sm_token_transfer',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx

		
	def sm_find_match(self, login, wif):
	
		ops = []
		json_body = {
						"match_type": 'Ranked',
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_find_match',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx

		
	def sm_submit_team(self, combo, id, login, wif):
	
		m = hashlib.md5()
		secret = ''.join([choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for i in range(10)])
		m.update((','.join(combo + [secret])).encode("utf-8"))
		team_hash = m.hexdigest()
		
		ops = []
		json_body = {
						"summoner": combo[0],
						"monsters": combo[1:],
						"trx_id": id,
						"app": self.app,
						"secret": secret,
						"team_hash": team_hash,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_submit_team',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx
		
		
	def sm_gift_cards(self, to, cards, login, wif):
	
		ops = []
		json_body = {
						"to": to,
						"cards": cards,
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_gift_cards',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx

		
	def sm_gift_packs(self, to, qty, edition, login, wif):
	
		ops = []
		json_body = {
						"to": to,
						"qty": qty,
						"edition": edition,		# ORB=2
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_gift_packs',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx

		
	def sm_claim_reward(self, id, login, wif):
	
		ops = []
		json_body = {
						"type": 'quest',
						"quest_id": id,
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_claim_reward',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx
		
	
	def sm_claim_reward_season(self, id, login, wif):
	
		ops = []
		json_body = {
						"type": 'league_season',
						"season": id,
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_claim_reward',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx
		
	
	def sm_start_quest(self, login, wif):
	
		ops = []
		json_body = {
						"type": 'daily',
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_start_quest',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx
	

	def sm_refresh_quest(self, login, wif):
	
		ops = []
		json_body = {
						"type": 'daily',
						"app": self.app,
					}
	
		op = {
			"required_auths": [],
			"required_posting_auths": [login],
			"id": 'sm_refresh_quest',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx
	

	def ssc_token_transfer(self, to, amount, from_account, wif, asset = 'DEC', memo = ''):
	
		ops = []
		json_body = {
						"contractName": 'tokens',
						"contractAction": 'transfer',
						"contractPayload": {
											"to": to,
											"quantity": str(amount),
											"symbol": asset,
											"memo": memo,
											"app": self.app,
											}
					}
	
		op = {
			"required_auths": [from_account],		#видимо потребуется активный ключ (((
			"required_posting_auths": [],
			"id": 'ssc-mainnet1',
			"json": json.dumps(json_body)
			}
		ops.append(['custom_json', op])

		tx = self.finalizeOp(ops, wif)
		return tx

		
#----- common def -----
def resolve_url(url):

	if '#' in url:
		url = url.split('#')[1]
	if '@' in url:
		url = url.split('@')[1]

	if url[-1:] == '/':
		url = url[:-1]

	if url.count('/') != 1:
		return([False, False])
	else:
		return(url.split('/'))
		
		
def resolve_body_ru(body):
	
	raw_body = []
	body = body.replace('#', '')
	body = body.replace('\n', '#')
	for s in body:
		if s in rus_list:
			raw_body.append(s)
		elif s == '#':
			#raw_body.append('\n')
			raw_body.append('#')
			
	if len(raw_body) == 0:
		return False
		
	return(''.join(raw_body))

