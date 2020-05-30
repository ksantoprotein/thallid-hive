# -*- coding: utf-8 -*-
#https://hive.hivesigner.com/

# https://developers.hive.io/quickstart/#quickstart-hive-full-nodes
nodes = [
		'https://api.hive.blog',
		'https://api.openhive.network',
		'https://anyx.io',
		'https://api.hivekings.com',
		'https://hived.privex.io',
		'https://rpc.ausbit.dev',
		]

prefix = 'STM'																		# 
#chain_id = 'beeab0de00000000000000000000000000000000000000000000000000000000'		# HIVE2 HF24
chain_id = '0000000000000000000000000000000000000000000000000000000000000000'		# HIVE HF23
time_format = '%Y-%m-%dT%H:%M:%S'													#OK
time_format_utc = '%Y-%m-%dT%H:%M:%S%Z'												#OK
expiration = 90

asset_precision = {
					"HIVE": 3,		#OK
					"VESTS": 6,		#OK
					"HBD": 3,		#OK
					}

#54321 Список транзакций по порядку для каждого БЧ он свой
# https://github.com/steemit/steem-js/blob/master/src/auth/serializer/src/ChainTypes.js
