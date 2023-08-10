from pydantic import BaseModel, validator
from typing import Dict
import json

class ItemType(BaseModel):
  name : str
  can_trade : bool

class Item(BaseModel):
  name : str
  amt : int
  item_type : ItemType

  @validator("amt")
  def check_amt_limit(cls, v):
    if v > 100:
      raise ValueError("Cannot have more than 100 amt of an item.")
    return v

class Inventory(BaseModel):
  items : Dict[str, Item]

def main():
  food_type = ItemType(
    name="food",
    can_trade=True
  )

  item1 = Item(
    name="Apple",
    amt=90,
    item_type=food_type
  )

  item2 = Item(
    name="Orange",
    amt=50,
    item_type=food_type
  )

  inventory = Inventory(
    items={"1": item1, "2": item2}
  )

  store = json.dumps(inventory.dict())
  print(store, type(store))

  print("Retriving Data")
  new = json.loads(store)
  reInv = Inventory(**new)


#json.load and dump acts as a way to go from dict to str
#then we take these and reload them into our models making it easier to read and understand


if __name__ == "__main__":
  main()