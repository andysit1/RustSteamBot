from app.models import RoomModel, LobbyModel, PlayerBet
from steam import Game
from typing import Callable
import time
from app.botCalls import BotTradeStream
import requests
#representation of a manager that handles the brokers
#should be able to take brokers and turn into json
#should be able to assign brokers and gather them on startup

rust_instance = Game(id=252490, name="Rust")

botCaller = BotTradeStream()

#manually links to my droplet servers...
botCaller.loadBotManually(ip="165.227.42.4:81")
botCaller.loadBotManually(ip="165.227.36.241:81")

# botCaller.loadBotManually(ip="localhost:82")

print(botCaller.getBestIP())

class CasinoManager:
    def __init__(self):
      self.active = False
      self.lobby : LobbyModel = LobbyModel(
        games={}
      )
      self.events = {
          "ACCEPTED" : self.handle_trade_accept,
          "DECLINE" : self.handle_trade_decline,
          "COUNTER" : self.handle_trade_counter,
          "SENT" : self.handle_trade_sent
        }

    #async function to load the bots into server.
    async def startup(self):
      await botCaller.loadbots()

    # BOT RETURN EVENTS
    async def handle_trade_accept(self, userid: str or int, roomid: str):
      print('Handling accept')

    async def handle_trade_decline(self, userid: str or int, roomid: str):
      print('Handle decline')

    async def handle_trade_counter(self, userid: str or int, roomid: str):
      print('Handle counter')

    async def handle_trade_sent(self, userid: str or int, roomid: str):
      print("Handle sent")

    async def handleEvent(self, payload: dict, userid: str or int):
      event = payload['action']
      handler: Callable = self.events.get(event)
      if handler:
          await handler(payload['roomid'], userid=userid)

    # #Check Logic
    # async def isTradeAccepted(self):



    #ACTIONS INVOKING BOT
    #finds the room and sets it active... then returns the room
    async def updateEndTime(self, roomID : str, changedTime : int):
      self.lobby.games[roomID].setEndtime(changedTime)
      # await botCaller.cancel_trade(userid=userid, roomid=roomID)

    #give it a lobby object and a broker to control the room
    async def startRoom(self, roomobj : RoomModel):
      print("Room has been created, ", roomobj.dict())
      self.lobby.games[roomobj.roomid] = roomobj
      # assigns an ip to the roomid...
      botCaller.setRoomIP(roomobj.roomid)
      payload = {
        "event" : "GET",
        "roomid": roomobj.roomid,
        "token": roomobj.players[0].token,
        "items": roomobj.players[0].items,
        "trade_type" : 0
      }

      self.lobby.games[roomobj.roomid].accepted = False
      await botCaller.trade(roomid=roomobj.roomid, steamid=roomobj.players[0].steamid, payload=payload)
    #assigns the opponent of the room, items, endtime and sends the request
    async def joinRoom(self, player : PlayerBet, payload):
      room = self.lobby.games[payload['roomID']]
      room.setAction("join")
      room.setEndtime(payload['endtime'])
      room.players.append(player)
      print("Updated: {}".format(room.dict()))

      payload = {
        "event" : "GET",
        "roomid": payload['roomID'],
        "token": player.token,
        "items": player.items,
        "trade_type" : 1
      }

      room.accepted = False
      await botCaller.trade(roomid=room.roomid, steamid=player.steamid, payload=payload)


    #note : status can be set to ended since its a matter of time till the timer ends
    #on join -> set the status to ended and empty the timmer. Send back the new data
    #only important for new users not the users already in the website...
    async def joinnedRoom(self, user : str):
      print("{} has joinned the room".format(user))
      for roomid in self.lobby.games:
        if self.lobby.games[roomid].isUserHere(user):
          self.lobby.games[roomid].setAction("join")
          self.lobby.games[roomid].setStatus("Ended");
          self.lobby.games[roomid].setEndtime("Empty");
          print("Updated room {}".format(self.lobby.games[roomid].getData()))
          await self.lobby.games[roomid].generateModSalt()
          return self.lobby.games[roomid].json()

    async def acceptedRoom(self, roomid : str):
      room : RoomModel = self.lobby.games.get(roomid)

      if len(room.players) == 1:
        print("phase 1 of room done {}".format(roomid))
        room.setAction("create")
        room.setStatus("Open")
        await room.generateServerSalt()
        room.getInterval(marginPercent=0.05)
        return room.getData()

      if len(room.players) == 2:
        room.setAction("join")
        room.setStatus("Ended")
        await room.generateModSalt()
        return room.getData()


    async def canceledRoom(self, roomid: str):
      room : RoomModel = self.lobby.games.get(roomid)

      if len(room.players) == 1:
        print("someone wants to close their room, remove the room entirely..")

      if len(room.players) == 2:
        print("player didnt accept so just remove them from the player list...")
        room.setStatus("Open")
        room.players.pop()
        await botCaller.cancel_trade(roomid=roomid)

    #called when user has joined the game
    #determines the winning person
    async def determineWinner(self, roomid: str):
      room : RoomModel = self.lobby.games[roomid]
      room.decideWinner()

      #this items should not have the include house commissions...
      items = await room.getHouseCommissions(percent=0.10)

      if items:
        payload = {
          "event" : "SEND",
          "roomid": roomid,
          "token": room.winner.token,
          "items": items,
          "trade_type" : 0
        }
        print("fake send", payload)
        await botCaller.trade(roomid=roomid, steamid=room.winner.steamid, payload=payload)

      return self.lobby.games[roomid].json()

    #saves the game details and such when this parts occurs
    async def gameHasEnded(self, roomID : str):
      print("Room {} has ended!!!".format(roomID))
      # #save db here...
      # #make a function to save all the data of the rooms and details...
      # room : RoomModel = self.lobby.games[roomID]

      # url = "http://localhost/save_game"
      # payload = {
      #   "roomid" : roomID,
      #   "winner" : room.winner.name,
      #   "amt" : room.winner.betAmt,
      #   "chance" : room.ticket,
      #   "isWinner" : False
      # }
      # requests.post(url=url, data=payload)

    #appends all ready rooms

    async def getRoomContext(self, roomid:str):
      return self.lobby.games[roomid].json()

    async def startRoomTimerCancel(self, timeAmt: int, roomid: str):
      time.sleep(timeAmt)
      if not self.lobby.games[roomid].isAccepted():
        print("CANCELING TRADE! should send a post request to cancel the trade...")
      else:
        print("Trade is accepted already! nothing happens...")

    async def jsonify(self):
      #if dict is empty then return no room
      if not self.lobby.games:
        print("no room found")

      self.lobby.setAction("init")
      return self.lobby.json()
