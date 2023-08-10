

#represents the bot trading server
  #handles the # of bots offloading each bot.


#        # requests.post("http://localhost:81/trade/{}".format(room.winner.steamid), data=json.dumps(payload))
import json
import requests
import os
import aiohttp
import random
# from pydantic import BaseModel
# class BotModel(BaseModel):


class BotTradeStream():
  def __init__(self):
    self.roomid_ip = {}
    self.ip_address = {}

  async def loadEnvBots(self):
    running = True
    count = 1

    #loads the bot based on the envoirnment variables on start-> ie BOT1 BOT2...
    #should create diction that maps to an integer of 0
    while running:
      ip = os.getenv("BOT{}".format(count))
      if ip:
        self.ip_address[ip] = 0
        count += 1
      else:
        running = False
        break

  def loadBotManually(self, ip: str):
    self.ip_address[ip] = 0


  #function to take in items
  def getBestIP(self):
    match = 1000000
    chose = None

    #should loop through all ip address and picks thet ip used less...
    for ip in self.ip_address:
      if self.ip_address[ip] < match:
        match = self.ip_address[ip]
        chose = ip

    self.ip_address[chose] += 1
    return chose

  def getRandomIP(self):
    return random.choice(list(self.ip_address.keys()))

  #maps the roomid to the best ip at the given time...
  def setRoomIP(self, roomid):
    picked = self.getBestIP()
    self.roomid_ip[roomid] = picked

  #use this function assumed that getRoomIP() is already called before hand.
  async def trade(self, roomid: str, steamid: str, payload: dict):
    ip = self.roomid_ip.get(roomid)
    url = "http://{}/trade/{}".format(ip, steamid)
    print(url, payload)
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(url, json=json.dumps(payload)) as response:
    #         print(response.text)
    #         print("sent!")

    requests.post(url=url, data=json.dumps(payload))

  async def getUserInfo(self, steamid: str):
    ip = self.getRandomIP()

    url = "http://{}/user/{}".format(ip, steamid)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response_data = await response.text()
            return response_data

  async def cancel_trade(self, roomid: str):
    ip = self.roomid_ip.get(roomid)
    url = "http://{}/trade_cancel/{}".format(ip, roomid)
    print(url)
    requests.post(url=url)
