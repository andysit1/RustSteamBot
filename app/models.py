from sqlalchemy import Column, Integer, String
from app.database import Base
from pydantic import BaseModel, validator
from typing import Dict, List, Optional
import steam
from app.utils import findBestSet
#representing a database for images

import hashlib
import requests
import random
import aiohttp

#holds items, lets us know when trades are sent, accepted, and other conditions
class BrokerBot(steam.Client):
  async def on_ready(self):  # on_events in a subclassed client don't need the @client.event decorator
    print("------------")
    print("Logged in as")
    print("Username:", self.user)
    print("ID:", self.user.id64)
    print("Friends:", len(await self.user.friends()))
    print("------------")

  async def on_trade_accept(self, trade: steam.TradeOffer):
    print(f"Accepted trade: #{trade.id}")
    print("Trade partner was:", trade.partner)

    url = "http://localhost:8000/accepted/{}".format(trade.partner.id64)

    async with aiohttp.ClientSession() as session:
        async with session.post(url):
            print("accepted trade!")

    #send a request notifying that the request went through
  async def on_trade_send(self, trade: steam.TradeOffer):
    print("Trade sent to", trade.partner)

  async def on_trade_cancel(self, trade: steam.TradeOffer):
    print("canceled")


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, index=True, primary_key=True)
    name = Column(String)
    url = Column(String)

class Players(Base):
    __tablename__ = "players"
    #represent steamID
    steamID = Column(Integer, index=True, primary_key=True)

    #long string representing all data in dict
    payload = Column(String)

# Models for storing the game information for future reference

#representation of a game of coinflip
class GameInfo(BaseModel):
    roomid: str
    winner : str
    amt : int
    chance : int
    isWinner : bool

#represents history of all games
#key : lobby id, #value : Game Info
class GameHistory(BaseModel):
    GameInfo : list[GameInfo]

#representation of a user in our system
#should hold name, desposited and their trade url... things to populate
class UserData(BaseModel):
    name : str
    avatarurl : str
    deposited : int = None
    won : int = None
    tradeToken : Optional[str]
    games : GameHistory = None

    def setTradeToken(self, token: str):
        self.tradeToken = token

    def updateGameHistroy(self, game : GameHistory):
        self.games.append(game)


#representation of a players BET
class PlayerBet(BaseModel):
    steamid : str or int
    pfp : Optional[str]
    token : Optional[str]
    name : Optional[str]
    betAmt : Optional[float]
    items : Optional[list]
    side : Optional[str]
    isHost : Optional[bool]
    winningPercent : Optional[float]

class RoomModel(BaseModel):
    host : str or int = None

    accepted : Optional[bool]
    action : Optional[str]
    roomid : Optional[str]
    endtimer : Optional[str]
    status : Optional[str]

    serversalt : Optional[str]
    hashToken : Optional[str]
    modsalt : Optional[str]


    ticket : Optional[float]
    betInterval : Optional[set]
    #representation of players (2 max)
    players : List[PlayerBet] = None
    winner : Optional[PlayerBet]


    @validator('players')
    def players_must_be_two(cls, v):
        if (len(v) > 2):
            raise ValueError("Room is full.")
        return v

    def getData(self) -> dict:
        return self.json()

    #setter functions
    def setMod(self, mod):
        self.modsalt = mod

    def setEndtime(self, endtime):
        self.endtimer = endtime

    def setAction(self, act : str):
        self.action = act

    def setRoomID(self, Rid):
        self.roomid = Rid

    def setStatus(self, changed):
        self.status = changed

    def isUserHere(self, steamID):
        for player in self.players:
            if player.steamid == steamID:
                return True

    def isAccepted(self):
        return self.accepted

    async def generateServerSalt(self):
        url = "https://www.random.org/strings/?num=1&len=15&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new"
        response = requests.get(url)

        if response.status_code == 200:
            self.serversalt = response.text.strip()
            self.hashToken = hashlib.sha256(self.serversalt.encode('utf-8')).hexdigest()
        print("Public hashkey: {} Private Key: {}".format(self.serversalt, self.hashToken))

    async def generateModSalt(self):
        url = "https://www.random.org/strings/?num=1&len=15&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new"
        response = requests.get(url)

        if response.status_code == 200:
            self.modsalt = "{}-{}".format(self.serversalt, response.text.strip())
        print("Mod {}".format(self.modsalt))


    #interval for user to join game
    def getInterval(self, marginPercent : float):
        if not len(self.players) > 1:
            margin = self.players[0].betAmt * marginPercent
            self.betInterval = (self.players[0].betAmt - margin, self.players[0].betAmt + margin)


    def decideWinner(self):
        if len(self.players) < 2:
            return

        random.seed(self.modsalt)
        self.ticket = random.random()
        print("The winning ticket percentage {}".format(random.random()))
        totalPot = self.players[0].betAmt + self.players[1].betAmt

        self.players[0].winningPercent = self.players[0].betAmt / totalPot
        self.players[1].winningPercent = self.players[1].betAmt / totalPot

        #blackside = left portion
        print("FLIPING------------------------")

        #base on the creating lobby make the other side diff
        if self.players[0].side == "BlackCOIN":
            self.players[1].side = "RedCOIN"
        else:
            self.players[1].side = "BlackCOIN"


        if self.players[0].side == "BlackCOIN":
            print("selecting blackcoin")
            # if the ticket value is greater then other player one
            if self.ticket > self.players[0].winningPercent:
                self.winner = self.players[1]
            else:
                self.winner = self.players[0]

        if self.players[1].side == "BlackCOIN":
            #else we are on the right portion
            if self.ticket > self.players[1].winningPercent:
                self.winner = self.players[0]
            else:
                self.winner = self.players[1]

        self.setAction("finished")
        #should send back the user data here ie, ticket, serversalt, modsalt,

    async def getHouseCommissions(self, percent: float):
        items = self.players[0].items + self.players[1].items
        houseCommish = await findBestSet(items=items, percent=percent)
        print("COMMISSIONS", houseCommish)

        for item in houseCommish:
            items.remove(item)

        print("FINAL TRADE BACK", items)
        return items

class LobbyModel(BaseModel):
    action : Optional[str]
    games : Dict[str, RoomModel] = None

    def setAction(self, action: str):
        self.action = action



  # Print the closest sum and the corresponding subset

#ADMIN PANEL
class GlobalStatistics(BaseModel):
    total_items_deposit : int
    total_items_deposit_today : int

    total_games_played : int
    total_games_played_today : int

    total_profit : int

    total_users_played : int
    total_users_played_today: int

class WebsiteVariables(BaseModel):
    slow_time_seconds : int
    min_deposit_money : int
    max_deposit_money : int
    active_games_at_once: int
