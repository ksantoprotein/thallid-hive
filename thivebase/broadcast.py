﻿# -*- coding: utf-8 -*-

import json
import struct
import time
import hashlib
import ecdsa

from pprint import pprint
from datetime import datetime, timedelta
from calendar import timegm
from binascii import hexlify, unhexlify

from .storage import expiration, time_format, time_format_utc, chain_id, prefix

from .base58 import Base58


class Tx():

	def __init__(self, rpc, **kwargs):

		self.rpc = rpc
		
		self.chain_id = chain_id
		self.prefix = prefix
		self.expiration = int(kwargs.pop("expiration", expiration))
		self.time_format = time_format
		self.time_format_utc = time_format_utc
		
	##### ##### broadcast ##### #####

	def finalizeOp(self, ops, wif):
	
		n = 1
		while n < 3:
			tx = self.constructTx(ops, wif)		# Строим начальную транзакцию

			#result = self.rpc.call('broadcast_transaction', tx)
			### если успешно, то ничего нет {} поэтому проверяем на тип данных False == bool
			result = self.rpc.call('broadcast_transaction_synchronous', tx) if tx else False
			if result:
				if not(isinstance(result, bool)):
					tx["block_num"] = result["block_num"]
					tx["id"] = result["id"]
					return tx
			print('finalizeOp', result, 'try constructTx', n)
			n += 1
		return False
		
		
	def constructTx(self, ops, wifs):
	
		tx = {
				"ref_block_num": None,		# construct
				"ref_block_prefix": None,	# construct
				"expiration": None,			# construct
				"operations": ops,
				"extensions": [],
				"signatures": []			# construct
				}
		
		# get_block_params
		# Auxiliary method to obtain ref_block_num and ref_block_prefix. Requires a websocket connection to a witness node!
		# Постоянно вылетает на это месте - обвязка через try
		n = 0
		while True:
			try:
				props = self.rpc.call('get_dynamic_global_properties')
				tx["ref_block_num"] = props["head_block_number"] & 0xFFFF
				tx["ref_block_prefix"] = struct.unpack_from("<I", unhexlify(props["head_block_id"]), 4)[0]
				break
			except:
				print('ERROR constructTx get_block_params')
				n += 1
				if n >= 10: return False
				time.sleep(1)
		
		# Properly Format Time that is x seconds in the future :param int secs: Seconds to go in the future (x>0) or the past (x<0)
		now = datetime.strptime(props["time"], self.time_format)
		new = timedelta(seconds=self.expiration) + now
		tx["expiration"] = new.strftime(self.time_format)
		
		digest = self.get_digest(tx)		# получаем хэш транзакции
		wifs = [wifs] if not(isinstance(wifs, list)) else wifs
		for wif in wifs: tx["signatures"].append(self.sign(wif, digest))	# получаем подпись\подписи
		
		return tx

		
	def get_digest(self, tx):
		
		hex = self.rpc.call('get_transaction_hex', tx)
		b2 = unhexlify(hex)
		b = b2[:-1]		#удаляем лишний байт в конце
		message = unhexlify(self.chain_id) + b															# chain_id + tx
		digest = hashlib.sha256(message).digest()
		
		return digest
		
		
	def sign(self, wif, digest):	### digest
	
		# Sign the message private key	
		p = bytes(Base58(wif, prefix=self.prefix))
		i = 0
		cnt = 0
		sk = ecdsa.SigningKey.from_string(p, curve=ecdsa.SECP256k1)
		
		while True:
			cnt += 1
			if not cnt % 20: print("Still searching for a canonical signature. Tried %d times already!" % cnt)

			# Deterministic k
			k = ecdsa.rfc6979.generate_k(
				sk.curve.generator.order(),
				sk.privkey.secret_multiplier,
				hashlib.sha256,
				hashlib.sha256(
					digest + struct.pack("d", time.time()) # use the local time to randomize the signature
				).digest())
			
			# Sign message
			sigder = sk.sign_digest(digest, sigencode=ecdsa.util.sigencode_der, k=k)

			# Reformating of signature
			r, s = ecdsa.util.sigdecode_der(sigder, sk.curve.generator.order())
			signature = ecdsa.util.sigencode_string(r, s, sk.curve.generator.order())

			# Make sure signature is canonical!
			lenR = sigder[3]
			lenS = sigder[5 + lenR]
			
			if lenR is 32 and lenS is 32:
				# Derive the recovery parameter
				pubkey = sk.get_verifying_key()
				### i = self.recoverPubkeyParameter(digest, signature, sk.get_verifying_key())
				for ii in range(0, 4):
					p = self.recover_public_key(digest, signature, ii)
					#if (p.to_string() == pubkey.to_string() or self.compressedPubkey(p) == pubkey.to_string()):
					if p.to_string() == pubkey.to_string(): break
				ii += 4		# compressed
				ii += 27	# compact
				break
		
		# pack signature
		sigstr = struct.pack("<B", ii)
		sigstr += signature

		sigs = hexlify(sigstr).decode('ascii')
		return sigs
		
		
	def recover_public_key(self, digest, signature, i):
		""" Recover the public key from the the signature
		"""
		# See http: //www.secg.org/download/aid-780/sec1-v2.pdf
		# section 4.1.6 primarily
		curve = ecdsa.SECP256k1.curve
		G = ecdsa.SECP256k1.generator
		order = ecdsa.SECP256k1.order
		yp = (i % 2)
		r, s = ecdsa.util.sigdecode_string(signature, order)
		# 1.1
		x = r + (i // 2) * order
		# 1.3. This actually calculates for either effectively
		# 02||X or 03||X depending on 'k' instead of always
		# for 02||X as specified.
		# This substitutes for the lack of reversing R later on.
		# -R actually is defined to be just flipping the y-coordinate
		# in the elliptic curve.
		alpha = ((x * x * x) + (curve.a() * x) + curve.b()) % curve.p()
		beta = ecdsa.numbertheory.square_root_mod_prime(alpha, curve.p())
		y = beta if (beta - yp) % 2 == 0 else curve.p() - beta
		# 1.4 Constructor of Point is supposed to check if nR is at infinity.
		R = ecdsa.ellipticcurve.Point(curve, x, y, order)
		# 1.5 Compute e
		e = ecdsa.util.string_to_number(digest)
		# 1.6 Compute Q = r^-1(sR - eG)
		Q = ecdsa.numbertheory.inverse_mod(r, order) * (s * R + (-e % order) * G)
		# Not strictly necessary, but let's verify the message for
		# paranoia's sake.
		if not ecdsa.VerifyingKey.from_public_point(
				Q, curve=ecdsa.SECP256k1).verify_digest(
			signature, digest, sigdecode=ecdsa.util.sigdecode_string):
			return None
		return ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1)

		
	def compressedPubkey(self, pk):
		order = pk.curve.generator.order()
		p = pk.pubkey.point
		x_str = ecdsa.util.number_to_string(p.x(), order)
		return bytes(chr(2 + (p.y() & 1)), 'ascii') + x_str

		
#----- main -----
if __name__ == '__main__':
	pass
	

