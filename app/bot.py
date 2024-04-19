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




