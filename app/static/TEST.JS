var data = {
  "host": "76561198309967258",
  "action": "finished",
  "roomid": "o99KSiuKKjY8BUm",
  "endtimer": 1686549130217,
  "status": "Ended",
  "serversalt": "MnR2F35eRL0SDMf",
  "hashToken": "a508152f561301f6264bedafee52af05f2d6386548f6a278ceff78fe130c4a25",
  "modsalt": "MnR2F35eRL0SDMf-OOpqzPjkJNaLSLK",
  "ticket": 0.2651068604935083,
  "betInterval": [0.9025, 0.9974999999999999],
  "players": [
    {
      "steamid": "76561198309967258",
      "name": null,
      "betAmt": 0.95,
      "items": ["Landscape Picture Frame", "Large Banner Hanging", "One Sided Town Sign Post"],
      "side": "BlackCoin",
      "isHost": null,
      "winningPercent": 0.39915966386554624
    },
    {
      "steamid": "76561199118573187",
      "name": null,
      "betAmt": 1.43,
      "items": ["Pizza Hide Shirt", "Shark Headwrap"],
      "side": "RedCoin",
      "isHost": null,
      "winningPercent": 0.6008403361344538
    }
  ],
  "winner": {
    "steamid": "76561198309967258",
    "name": null,
    "betAmt": 0.95,
    "items": ["Landscape Picture Frame", "Large Banner Hanging", "One Sided Town Sign Post"],
    "side": "BlackCoin",
    "isHost": null,
    "winningPercent": 0.39915966386554624
  }
};



function populateViewModel(object){
  console.log("POPULATE OBJECT", object);
  if (object.action === "finished"){
    var player1 = object.players[0];
    var player2 = object.players[1];
    console.log("PLAYER1:", player1.betAmt, player1.items.length, player1.winningPercent);
    console.log("PLAYER2:", player2.betAmt, player2.items.length, player2.winningPercent);

    console.log("HASH", object.hashToken);
    console.log("SALT", object.serversalt);
    console.log("MOD", object.modsalt);
    console.log("TICKET", object.ticket)
    console.log("SIDE WON", object.winner.side)
  }
}
populateViewModel(data);