import os, sys
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
import json

# Not ideal, but for the sake of an example
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))
from fastapi.staticfiles import StaticFiles
#data base imports
from sqlalchemy.orm import Session

import app.models as models
from app.database import engine, sessionLocal
#Import my bot commands


app = FastAPI()
script_dir = os.path.dirname(__file__)
st_abs_file_path = os.path.join(script_dir, "static/")
temp_abs_file_path = os.path.join(script_dir, "templates")

app.mount("/static", StaticFiles(directory=st_abs_file_path), name="static")
templates = Jinja2Templates(directory=temp_abs_file_path)

from steam import SteamID

#password instance
models.Base.metadata.create_all(bind=engine)

from app.routers import user, gamelogic
app.include_router(user.router)
app.include_router(gamelogic.router)

def getDB():
  try:
    db = sessionLocal()
    yield db
  finally:
    db.close()

import asyncio
@app.on_event("startup")
async def startup_event():
  print("starting")

#FAST FIX -> storing until application crashes...

import json
from app.botCalls import BotTradeStream
botCaller = BotTradeStream()
botCaller.loadBotManually(ip="165.227.42.4:81")
botCaller.loadBotManually(ip="165.227.36.241:81")
# botCaller.loadBotManually(ip="localhost:82")
#returns the user data if it exist
async def isUserRegistered(userid: str, userInformation):
  if userInformation:
    playerINFO = models.UserData(**json.loads(userInformation.payload))

    context = {
      "steam_id" : userid,
      "trade_token" : playerINFO.tradeToken,
      "profile_info" : playerINFO.json(),
    }
    return context

  #if not in then...
  return None
#some data is only accessable by the api call
@app.get('/')
async def main(request: Request, db : Session = Depends(getDB)):
  userid = request.cookies.get("SteamID")
  if userid:
    userInformation = db.query(models.Players).filter(models.Players.steamID == userid).first()
    context = await isUserRegistered(userid=userid, userInformation=userInformation)
    print(context)

    if not context:
      data = await botCaller.getUserInfo(steamid=userid)
      processed_data = json.loads(data)

      userModel = models.UserData(
          name=processed_data['payload']['name'],
          avatarurl=processed_data['payload']['avatar']
      )

      newModel = models.Players(
        steamID = int(userid),
        payload = json.dumps(userModel.dict())
      )

      db.add(newModel)
      db.commit()
      db.refresh(newModel)
      print("{} has been stored".format(userModel.name))

      context = newModel.json()

    response = templates.TemplateResponse("userIndex.html", {"request": request, "context" : context})
  else:
    response = templates.TemplateResponse("index.html", {"request": request})
  return response


@app.post("/updateTradeToken/{userid}/{token}")
async def updateToken(userid: str, token: str, db : Session = Depends(getDB)):
  print("trying to updateing token...")
  userInformation : models.Players = db.query(models.Players).filter(models.Players.steamID == userid).first()
  print(userInformation, type(userInformation))

  data = models.UserData(**json.loads(userInformation.payload))
  data.setTradeToken(token)
  userInformation.payload = json.dumps(data.dict())

  db.add(userInformation)
  db.commit()
  db.refresh(userInformation)


@app.post("/save_game")
async def saveGame(game: models.GameInfo, db : Session = Depends(getDB)):
  print("Saving:", game.winner, game.roomid, game.amt, game.chance)
  # userInformation : models.Players = db.query(models.Players).filter(models.Players.steamID == userid).first()
  # data : models.UserData = models.UserData(**json.loads(userInformation.payload))
  # data.games.GameInfo.append(game)
  # userInformation.

