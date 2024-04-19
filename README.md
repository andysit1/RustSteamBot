# RustSteamBot
The project I worked on over the 2023 summer. There's a lot of problems with this and this is the oldest version of the project from structure, language choice, and overall I changed all the aspects of the project. Feel free to check it out as I'm not using this anymore.

If you wanted to improve from this state I would suggest...

Separate the front end from the backend, right now it serves the HTML page when pinged on address but this is a terrible idea since if the backend crashes the entire site goes out. Try creating a front that only takes API requests from the external backend. Also, the socket connection should never be entangled with the backend as it creates problems.

Another important part is having a way to validate actions on the backend based on game data. Looking back there was a problem where I was worried about hacking or security problems. If you make all actions validated based on current game information then it's hard to hack into the system since if they tried to abuse the bots it wouldn't work unless it made sense relative to the game state.

Lastly, inorder to bypass API restrictions I would suggest getting a proxy instead of the rotating address, it's easier and scales better. The cost is worth it in my opinion.

