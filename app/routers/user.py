from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from pysteamsignin.steamsignin import SteamSignIn
from fastapi_utils.tasks import repeat_every
import requests

from app.utils import *
from app.config import IP

AUTHENTICATION_TOKENS = []
marketValues : dict
#ROUTE USER
#deals with anything related to the user ie login, logout, data to be fetched...

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)

#this route should handle
async def getAuthToken():
  url = "https://www.random.org/strings/?num=1&len=20&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new"
  response = requests.get(url)
  if response.status_code == 200:
    return response.text.strip()
  else:
    print("error getting string")

async def fetchMarketPrice():
  url = "https://api.steamapis.com/market/items/252490?format=compact&api_key=xIBOC04eLmEpu-8HGYUyYNWeXSA";
  res = requests.get(url=url)

  if res.status_code == 200:
    return res.json()

marketValues : dict
@router.on_event("startup")
@repeat_every(seconds=1800)
async def updateMarketItems():
  print("Market Prices Updating...")
  global marketValues
  marketValues = await fetchMarketPrice()

async def fetchUserInventory(userid : str):
  url = "https://api.steamapis.com/steam/inventory/{}/252490/2?api_key=xIBOC04eLmEpu-8HGYUyYNWeXSA".format(userid);
  res = requests.get(url=url)

  if res.status_code == 200:
    data = res.json()
    if data["total_inventory_count"] != 0:
      inventory = processRawInventory(data=data)
      for item in inventory:

        #grabs the market Values..
        price = marketValues.get(item['market_hash_name'])
        item['price'] = price
    else:
      return {'message': 'no items in inventory'}
  return inventory

@router.get("/inventory/{userid}")
async def returnInventory(request: Request, userid: str):

  authToken = request.cookies.get("auth_token")
  if not authToken:
    return HTMLResponse("Not Authorized to use this endpoint. Login please before trying again")

  if authToken not in AUTHENTICATION_TOKENS:
    return HTMLResponse("Not Authorized to use this endpoint. Login please before trying again")

  if not userid:
    return HTMLResponse("No userID was entered")

  return await fetchUserInventory(userid=userid)

#send the user to a third client login
@router.get('/login')
def login():
  steamLogin = SteamSignIn()
  return steamLogin.RedirectUser(steamLogin.ConstructURL('http://{}:80/user/processlogin/'.format(IP)))


@router.get('/logout')
def logout(request: Request, response : Response):
  print("logout user...")
  token = request.cookies.get("auth_token")

  response = RedirectResponse(url="/")
  if token:
    response.delete_cookie("auth_token")
    if token in AUTHENTICATION_TOKENS:
      AUTHENTICATION_TOKENS.remove(token)
  response.delete_cookie("SteamID")

  return response

#when accepted this will process id and save to a cookie and redirect to the main index
#able to add other filtering in the future if needed
@router.get('/processlogin/')
async def process(request : Request, response : Response):
  steamLogin = SteamSignIn()
  steamID = steamLogin.ValidateResults(request.query_params)

  auth_token = await getAuthToken()
  AUTHENTICATION_TOKENS.append(auth_token)

  response = RedirectResponse(url="/")
  response.set_cookie(key="SteamID", value=steamID, domain=IP, httponly=True, secure=False, max_age=3600)
  response.set_cookie(key="auth_token", value=auth_token, domain=IP, httponly=True, max_age=3600)
  return response
