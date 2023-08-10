import json
from fastapi import WebSocket, APIRouter
from app.models import PlayerBet, RoomModel
from app.websocketLogic import ConnectionManager, WebSocketDisconnect
from app.roomBot import CasinoManager
from typing import Callable


roomManager = CasinoManager()
manager = ConnectionManager()

router = APIRouter(
    prefix="/game",
    tags=["game"],
    responses={404: {"description": "Not found"}},
)

#HELPER FUNCTIONS
import requests
async def getRoomID():
  url = "https://www.random.org/strings/?num=1&len=15&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new"
  response = requests.get(url)
  if response.status_code == 200:
    return response.text.strip()
  else:
    print("error getting string")

@router.post('/accepted/{roomid}')
async def on_accept(roomid : str):
  createRoomJson = await roomManager.acceptedRoom(roomid=roomid)
  await manager.broadcast(createRoomJson)
  #start timer here to start the flip...

#should remove the canceled room from the player list and send a request to server to cancel the trade..
@router.post('/canceled/{roomid}')
async def on_cancel(roomid : str):
  await roomManager.canceledRoom(roomid=roomid)

@router.get('/room/{roomid}')
async def get_room_by_id(roomid: str):
  data = await roomManager.getRoomContext(roomid=roomid)
  return data




#EVENT FUNCTIONS FOR WEBSOCKET

#this is the global timer starter
async def startTimer(timerType: str, roomid : str, time : int):
  # when using sends a join request we need to start the timeres on the server...
  updateDict = {}
  updateDict['action'] = "timerStart"
  updateDict['intent'] = timerType
  updateDict['timeAmount'] = time
  updateDict['roomid'] = roomid

  #if we are trying to get items then we want to have cancel function at the end...
  await manager.broadcastJSON(updateDict)


#this is a the interface for recieving data from websocket
async def handle_trade_offer(payload : dict, user : str):
  event = payload['action']
  if event == "tradeOffer":
    if payload["intent"] == "create":
      playerobj = PlayerBet(
        name=payload['name'],
        steamid=user,
        betAmt=payload['betAmt'],
        items=payload['content'],
        side=payload['side'],
        token=payload['token'],
        pfp=payload['sender_pfp']
      )

      roomobj = RoomModel(
        host = user,
        action = payload['action'],
        roomid = await getRoomID(),
        endtimer = payload['endtime'],
        players = [playerobj]
      )
      await roomManager.startRoom(roomobj)

    if payload["intent"] == "joinning":
      playerobj = PlayerBet(
        steamid=user,
        betAmt=payload['betAmt'],
        items=payload["content"],
        side=payload['side'],
        token=payload['token'],
        pfp=payload['sender_pfp'],
        name=payload['name']
      )

      #tells ther server to start all lobby timers
      await startTimer(timerType="TRADE" , roomid=payload["roomID"], time=90)

      #changes vars of room and send trade which has it's own timer...
      await roomManager.joinRoom(player=playerobj, payload=payload)

  #sets the new endtimer so when new user refresh the page they can see the timers
  #it also sends out the json on trigger inorder to start the timers of the users on the site already
async def handle_user_joined_game(payload: dict, user: str):
    await roomManager.updateEndTime(payload['roomID'], payload['endtime'])
    await startTimer("GAME", payload['roomID'], 10)
    finaljson = await roomManager.determineWinner(roomid=payload['roomID'])
    print("FINAL", finaljson)
    await manager.broadcastJSON(finaljson)


async def handle_game_ended(payload: dict, user: str):
  await roomManager.gameHasEnded(roomID=payload['roomID'])

async def handle_message(payload: dict, user: str):
  text = payload['content']
  await manager.broadcast(f"Client #{user} says: {text}")

event_handlers = {
    "tradeOffer": handle_trade_offer,
    "userJoinnedGame": handle_user_joined_game,
    "gameEnded": handle_game_ended,
    "message": handle_message,
}

#event handling function
async def eventHandler(payload: dict, user: str):
    event = payload['action']
    handler: Callable = event_handlers.get(event)
    if handler:
        await handler(payload, user)

#websocket connection
#this will control the two inputs of starting and joinning rooms
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
  await manager.connect(websocket)
  try:
    #before we start the website we need tog et the timmers of the rooms that are waiting...
    initialRoomData = await roomManager.jsonify()
    print(initialRoomData)
    await manager.send_personal_json_room(initialRoomData, websocket)
  except:
    print("error Loading data...")
  try:
      while True:
          data = await websocket.receive_text()
          try:
            json_data = json.loads(data)
            print("json data", json_data, type(json_data))

            #handles the events
            await eventHandler(user=client_id, payload=json_data)

          except json.JSONDecodeError:
            print("json decoding error, figure later...")
  except WebSocketDisconnect:
      manager.disconnect(websocket)
      await manager.broadcast(f"Client #{client_id} left the chat")

