import steam

#only purpose to pull data on users...
rust_instance = steam.Game(id=252490, name="Rust")

class MyClient(steam.Client):
    async def on_ready(self):
        print("------------")
        print("Logged in as")
        print("Username:", self.user)
        print("ID:", self.user.id64)
        print("Friends:", len(await self.user.friends()))
        print("------------")



# def tradeItems(username: str, password: str, shared_secret: str, identity_secret: str, trade_token: str or int, user_id : str or int, items_to_send: list):
#     functionClient = MyClient(trade_token=trade_token, user_id=user_id, items_to_send=items_to_send)
#     functionClient.run(username=username, password=password, shared_secret=shared_secret, identity_secret=identity_secret)


# tradeItems(username="polishedsnake",
#             password="q2cmX#Ay",
#             shared_secret="sSaYQjQ7NzufUyEJ0ODEqyKa8gU=",
#             identity_secret="l1s5nHt8vpzIcAySerduBeI0Bws=",
#             trade_token="MM6cAEpF", user_id="76561198309967258",
#             items_to_send=['Black Bandana']
#             )

