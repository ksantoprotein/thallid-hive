# thallid-hive - Python Library for Hive

Thallid-Hive библиотека для блокчейна Hive


# Installation

https://github.com/ksantoprotein/thallid-hive.git

# Documentation

### Поддерживает broadcast следующих операций


Используется broadcast_transaction_synchronous и функция возвращает tx транзакции добавляя в нее номер блока и trx_id

![](https://i.imgur.com/OrR7Bj9.png)


# Usage examples

#### Transfer/Transfers
``` python
from thivebase.api import Api

b4 = Api()

to = 'thallid'
amount = '0.001'
asset = 'GOLOS'
memo = 'test'
from_account = 'ksantoprotein'
wif = '5...'

b4.transfer(to, amount, asset, from_account, wif, memo=memo)

```

