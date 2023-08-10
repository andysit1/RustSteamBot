
var items = [];
var totalInventoryCost = 0;
let currentRoom = ""
timers = []

class Timer {



  constructor({ seconds, roomID }) {

    //When a new timer starts for that given roomid we want it to stop and start this timer as the new one
    if (timers[roomID]){
      timers[roomID].stopTimer();
      delete timers[roomID];
    }

    this.seconds = seconds;
    this.roomID = roomID;
    console.log("Timer started");
    this.interval = setInterval(() => this.updateTimer(roomID), 1000);
  }

  updateTimer(roomID) {
    this.seconds--;
    setStatus(roomID, 12, this.seconds);

    if (this.seconds <= 0) {
      console.log("Timer ended");
      this.stopTimer();
      setStatus(roomID, 12, "Open");
    }
  }

  stopTimer() {
    clearInterval(this.interval);
  }
}

class GameTimer extends Timer{
  updateTimer(roomID){
    this.seconds--;
    setStatus(roomID, 12, this.seconds);

    if (this.seconds <= 0) {
      this.stopTimer();
      setStatus(roomID, 12, "Ended");
    }
  }
}

function countItems(){

  const div = document.getElementById('inventoryModal');
  const imagesInInventory = div.querySelectorAll("span");
  console.log("COUNTING ITEMS");
  let invItemCount = 0
  imagesInInventory.forEach(image => {
    if (image.classList.contains("imgChked")){
      let imgEle = image.querySelector("img");
      console.log(imgEle.name);
      invItemCount++;
    }
  })

  console.log(invItemCount);
  return invItemCount;
}

function getItems(){
  const div = document.getElementById('inventoryModal');
  const imagesInInventory = div.querySelectorAll("span");
  console.log("COUNTING ITEMS");
  let fakeItemDB = []
  imagesInInventory.forEach(image => {
    if (image.classList.contains("imgChked")){
      let imgEle = image.querySelector("img");
      let price = imgEle.getAttribute("item_price")
      let data = [imgEle.name, price, imgEle.src];
      totalInventoryCost += parseFloat(price);
      console.log(data);

      fakeItemDB.push(data);
    }
  })

  console.log(fakeItemDB);
  return fakeItemDB
}

function objectify(data){
  var objectable = false;
  prasedData = data;

  while (!objectable){
    prasedData = JSON.parse(prasedData);
    if (typeof(prasedData) === 'object'){
      objectable = true
    }
  }
  return prasedData
}


function processObject(data){
  let s = objectify(data)
  console.log(s)
  return s
}


// reloads all the imgs with checkable
function loadImgSelectors(){
  console.log("Adding function to images")

  $("img.checkable").imgCheckbox({
    onload: function(){
      console.log("images are being set up!")
      // Do something fantastic!
    },
    onclick: function(el){
      imgEl = el.children()[0];  // the img element
      countItems();
    }
  });
}


function setStatus(roomID,cellIndex, status) {
  console.log(roomID, status);
  let row = document.getElementById(roomID)
  if (row){
    let cells = row.getElementsByTagName('td');
    if (cellIndex < cells.length){
      let cell = cells[cellIndex];
      cell.innerHTML = status
    }else{
      console.log("Cell index is out of range.");
    }
  }else{
    console.log("Row Id does not exist.");
  }
}


function populateInventory(market_hash_name, icon_url, price, id){
  console.log("Populating Inventory!")
  const div = document.getElementById('inventoryModal');

  var img = document.createElement('img');
  img.className = 'checkable';
  img.style.maxWidth = '120px';
  img.style.maxHeight = '100px';
  img.src = "https://steamcommunity-a.akamaihd.net/economy/image/" + icon_url
  img.title = market_hash_name + " $" + price;
  img.name = market_hash_name;
  img.id = id
  img.alt = market_hash_name;
  img.setAttribute("item_price", price)
  div.appendChild(img)
}


// takes the counted items and adds a new "amount" in elements
function adjustAmountItems(data){
  console.log("Adjusting the list...")
  const div = document.getElementById('inventoryModal');
  while (div.firstChild) {
    div.removeChild(div.firstChild);
  }

  data.forEach(element => {
    for (let i = 0 ; i < element['amt']; i++){
      //creates the img objects and populates the modal with the data
      populateInventory(element['market_hash_name'], element['icon_url'], element['price'], i);
    }
  });

  //makes the images clickable and functional
  loadImgSelectors();
}

// pulls the data from api and uses the helper functions produce on array that we need
function fetchInventory(userid){
  var url = location.href+"user/inventory/" + userid;
  console.log(url);
  fetch(url)
  .then(res => res.json())
  .then(data => {
    return adjustAmountItems(data);
  })
  .catch(error => {
    console.log("Error fetching data wait a few seconds:", error)
    throw error
  })
}



$(document).ready(function() {

  // Function to make multiple rooms
  function readRoomsData(data) {
    try{
      //loops through dictionary and makes room elements
      for (const roomid in data){
        if (!(data[roomid].status === null)){
          makeRoomElement(data[roomid])
        }
      }

    }catch(error){
      //if an error occurs then it means
      makeRoomElement(data)
    }
  }

  // Websocket Receiever
  ws.onmessage = function(event) {

    try{
      console.log("RAW DATA", event.data)
      let roomData = objectify(event.data)
      console.log(roomData, typeof(roomData))

      if (typeof(roomData) === 'object'){
        console.log("ACTION", roomData.action)

        if (roomData.action === 'init'){
          readRoomsData(roomData.games)
        }

        //after the init... diff dictionary structure
        if (roomData.action === 'create'){
          makeRoomElement(roomData)
        }

        // on join we want to end the timer and change the status to full
        if (roomData.action === 'join'){
          let payload = {
            "action" : "userJoinnedGame",
            "roomID" : roomData.roomid,
            "endtime" : Date.now() + 10 * 1000
          }

          if (ws.readyState === WebSocket.OPEN) {
            // Connection is open, send the message
            ws.send(JSON.stringify(payload));
          } else {
            // Connection is closed, handle the error or queue the message for later
            console.log("WebSocket connection is closed. Message not sent.");
          }
        }

        if (roomData.action === 'update'){
          updateRoom({roomData: roomData})
        }

        //waits for a ping to start timer of a given roomid
        if (roomData.action === 'timerStart'){
          if (roomData.intent === 'TRADE'){
            timers[roomData.roomid] = new Timer({seconds: roomData.timeAmount, roomID : roomData.roomid});
          }

          if (roomData.intent === 'GAME'){
            timers[roomData.roomid] = new GameTimer({seconds : roomData.timeAmount, roomID : roomData.roomid});
          }
        }
        console.log("Is Object...")
      }
    }catch{
      var messages = document.getElementById('messages')
      var message = document.createElement('li')
      var content = document.createTextNode(event.data)
      message.appendChild(content)
      messages.appendChild(message)
    }
  };

  // Fetch Room Information
  function fetchRoomInformation(roomid){
    var url = location.href+"game/room/" + roomid.toString();
    console.log(url);
    fetch(url)
    .then(res => res.json())
    .then(data => {
      var data = objectify(data);
      populateViewModel(data)
    })
    .catch(error => {

      console.log("Error fetching data wait a few seconds:", error)
      throw error
    })
  }

  function populateViewModel(object){
    console.log("POPULATE OBJECT", object);

    var player1 = object.players[0];
    var player2 = object.players[1];

    // MUST PROPERTIES
    document.getElementById("roomIdentification").innerHTML = "roomid: " + object.roomid;
    document.getElementById("hashtoken").innerHTML = "hash: " + object.hashToken;


    const row = 1;
    const col = 3;

    // REMOVE ITEMSHOWCASE
    let itemShowCase1 = document.getElementById("player1Items");
    let itemShowCase2 = document.getElementById("player2Items");

    for (let y = 0; y <= row; y++){
      for (let x = 0; x <= col; x++){
        try{
          let cell1 = itemShowCase1.rows[y].cells[x].querySelector(".viewItemImg");
          let cell2 = itemShowCase2.rows[y].cells[x].querySelector(".viewItemImg");

          cell1.src = "";
          cell2.src = "";

          console.log("cleared..")
        }catch{
          console.log("Link Broken");
          break
        }
      }
    }

    if (player1){
      console.log("Player1 ", player1);

      document.getElementById("player1pfp").src = player1.pfp;
      document.getElementById("player1NameTag").textContent = player1.name + " " + player1.side
      document.getElementById("player1Value").innerHTML = "$" + player1.betAmt;
      document.getElementById("player1ItemAmt").innerHTML = player1.items.length + " items";
      document.getElementById("player1WinCondition").innerHTML = player1.winningPercent + "%";


      // fill in item showcase
      let count = 0;
      for (let y = 0; y <= row; y++){
        for (let x = 0; x <= col; x++){

          try{
            let srcLink = player1.items[count][2];
            console.log("X ", x, "Y", y, "INDEX", count);

            if (srcLink){
              let cell = itemShowCase1.rows[y].cells[x].querySelector(".viewItemImg");
              cell.src = srcLink;
              cell.title = "$" + player1.items[count][1];
            }

            count++;
          }catch{
            console.log("Link Broken", count);
            break
          }
        }
      }

      if (player1.winningPercent == null){
        document.getElementById("player1WinCondition").innerHTML = "Empty"
      }else{
        document.getElementById("player1WinCondition").innerHTML = player1.winningPercent + "%";
      }
    }


    if (player2){
      console.log("Player2 ", player2);

      document.getElementById("player2pfp").src = player2.pfp;

      document.getElementById("player2Value").innerHTML = "$" + player2.betAmt;
      document.getElementById("player2ItemAmt").innerHTML = player2.items.length + " items";
      document.getElementById("player2NameTag").textContent = player2.name + " " + player2.side

      const row = 1;
      const col = 3;

      // fills in the item show case
      let count = 0;
      for (let y = 0; y <= row; y++){
        for (let x = 0; x <= col; x++){

          try{
            let srcLink = player2.items[count][2];

            if (srcLink){
              let cell = itemShowCase2.rows[y].cells[x].querySelector(".viewItemImg");
              cell.src = srcLink;
              cell.title = "$" + player2.items[count][1];
            }

            count++;
          }catch{
            break
          }
        }
      }

      if (player2.winningPercent == null){
        document.getElementById("player2WinCondition").innerHTML = "Empty"
      }else{
        document.getElementById("player2WinCondition").innerHTML = player2.winningPercent + "%";
      }
    }


    if (object.action === "finished"){
      document.getElementById("modsalt").innerHTML = "Mod: " + object.modsalt + " Ticket: " + object.ticket;
      var winCoinImg = document.createElement("img")
      winCoinImg.setAttribute("class", "winningCoin")
      winCoinImg.src = "static/"+ object.winner.side +".png"

      // object.winner.side
      modal2.appendChild(winCoinImg);
    }
  }

  function makeRoomElement(room){

    var row = document.createElement('tr');
    row.id = room.roomid;

    var profileCell = document.createElement('td');
    var hostPFP = document.createElement("img");
    hostPFP.src = room.players[0].pfp;
    hostPFP.classList.add("circle-image");
    profileCell.appendChild(hostPFP);

    console.log("Image URL:", room.players[0].pfp);
    console.log("Image Element:", hostPFP);
    row.appendChild(profileCell);


    for (let j = 0; j < 10; j++) {
      var emptyCell = document.createElement('td');
      row.appendChild(emptyCell);
    }

    var valueCell = document.createElement('td');
    valueCell.textContent = room.players[0].betAmt;
    row.appendChild(valueCell);

    var statusCell = document.createElement("td");

    if (room.endtime !== 'Empty'){
      let currentTime = room.endtime - Date.now()
      // still active timer
      if (currentTime >= 0){
        let timerTime = Math.round( currentTime / 1000 )
        timers[room.roomid] = new Timer({seconds: timerTime, roomID : room.roomID});
      }else{
        // timer is less than 0 and is already over so just set as room.status aka Ended
        statusCell.textContent = room.status;
      }
    }

    if (room.endtime === 'Empty'){
      statusCell.textContent = room.status;
    }

    row.appendChild(statusCell);

    var buttonCell = document.createElement("td");

    var button = document.createElement("button");



    button.addEventListener('click', () => {
      modal.showModal();
      fetchInventory(user);
      intent = "joinning";
      currentRoom = room.roomid;
    })

    button.id = room.user;
    button.textContent = 'Join';


    var button2 = document.createElement("button");
    button2.addEventListener('click', () => {
      fetchRoomInformation(room.roomid);
      modal2.showModal();
    })

    button2.textContent = 'View';

    buttonCell.appendChild(button);
    buttonCell.appendChild(button2);
    row.appendChild(buttonCell);

    tableBody.appendChild(row);
  }
  $("img.RadioCheckable").imgCheckbox({
    "radio" : true,
    "graySelected": false,
    onload: function(){
      // Do something fantastic!
    },
    onclick: function(el){
      var isChecked = el.hasClass("imgChked"),
      imgEl = el.children()[0];  // the img element
      console.log(imgEl.name + " is now " + (isChecked? "checked": "not-checked") + "!");
      side = imgEl.name;
    }
  });

  function updateRoom(roomData){
    console.log("Updating room with...", roomData)
  }

  const tradeButton = document.getElementById("tradeSubmit");
  const tradeInputArea = document.getElementById("tradeUrlInput");

  tradeButton.addEventListener('click', () => {
    var url = location.href + "updateTradeToken/" + user + "/" + tradeInputArea.value.slice(-8);
    console.log(url);
    fetch(url, {
      method: 'POST'
    })

    trade_token = tradeInputArea.value.slice(-8);
  })
  const submitModal = document.querySelector(".submit-button");

  submitModal.addEventListener('click', () => {
    items = getItems();
    if (items.length != 0){
      console.log("Submit");

      let dictContainer = {
        "action" : "tradeOffer",
        "intent" : intent,
        "betAmt" : parseFloat(totalInventoryCost).toFixed(2),
        "content" : items,
        "roomID" : currentRoom,
        "side" : side,
        "name" : profile_object.name,
        "token" : trade_token,
        "sender_pfp" : profile_object.avatarurl,
        "endtime" : Date.now() + 90 * 1000
      }
      console.log("Sending", JSON.stringify(dictContainer))

      if (ws.readyState === WebSocket.OPEN) {
        // Connection is open, send the message
        ws.send(JSON.stringify(dictContainer));
      } else {
        // Connection is closed, handle the error or queue the message for later
        console.log("WebSocket connection is closed. Message not sent.");
      }
    }
  })

  // {/* <img class="checkable" style="max-width: 120px; max-height: 100px;" :src="item.image_url" :title="item.market_hash_name":name="item.market_hash_name" :alt="item.market_hash_name"> */}



});



