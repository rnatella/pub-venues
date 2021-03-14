#!/bin/bash

TOR_CONFIG=/usr/local/etc/tor/torrc

tor_password="scholarly_password"
hashed_password=$(tor --hash-password $tor_password)
echo "ControlPort 9051" | tee $TOR_CONFIG
echo "HashedControlPassword $hashed_password" | tee -a $TOR_CONFIG

#sudo service tor stop
#sudo service tor start
brew services restart tor
