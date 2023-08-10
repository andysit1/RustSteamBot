
def count_items(assets):
  items = {}
  for asset in assets:
    itemCount = items.get(asset['classid'], 0)
    itemCount += 1
    items[asset['classid']] = itemCount
  return items
# count_items(data['assets'])

def adjustAmountItems(descriptions, count_items):
  final = []
  for desc in descriptions:
    if desc['marketable'] == 1:
      desc['amt'] = count_items[desc['classid']]
      final.append(desc)
  return final

def processRawInventory(data):
  return adjustAmountItems(descriptions=data['descriptions'], count_items=count_items(data['assets']))

import itertools
def sumList(values):
    total = 0
    for value in values:
        total += float(value[1])
    return total

def generate_power_set(s):
    power_set = []
    n = len(s)

    # Generate subsets of all sizes from 0 to n
    for r in range(n + 1):
        # Generate combinations of size r from the set
        subsets = itertools.combinations(s, r)
        power_set.extend(subsets)

    return power_set


def getHouseCom(power_set, target):
    lower = 0
    lowerSet = []

    for pset in power_set:
        sumC = sumList(pset)

        if len(pset) > 2:
            continue

        if sumC > lower and sumC <= target:
            lower = sumC
            lowerSet = pset

    return lowerSet

#return the highest combination of items closes to target...
async def findBestSet(items:list, percent: float):
  allSet = generate_power_set(items)
  target = sumList(items) * percent

  return getHouseCom(power_set=allSet, target=target)
  # print(getHouseCom(setData, 0.50))

