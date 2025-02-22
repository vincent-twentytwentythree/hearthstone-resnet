from douzero.env.clean_strategy import calc_clean
from douzero.env.simulate_card import SimulateCard, Result, Action
from douzero.env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone, HearthStoneById, GameEnv
from douzero.dmc.http_server_util import getCoreCard
def case2():
    meCardDetails = [
        {
            "cardId": "REV_290",
            "type": "LOCATION",
            "attack": 0, 
            "hp": 3, 
            "entityId": "0", 
            "playedRound": -1, 
            "area": "PlayArea",
            "isActive": True,
            "card": {
            },
            "cost": 0
        },
        {
            "cardId": "SW_446", 
            "type": "MINION",
            "attack": 1, 
            "hp": 2, 
            "entityId": "1", 
            "playedRound": -1, 
            "area": "PlayArea",
            "isActive": False,
            "card": {
            },
            "cost": 0
        },
        {
            "type": "MINION",
            "cardId": "SW_444", 
            "attack": 2, 
            "hp": 3, 
            "entityId": "2", 
            "playedRound": -1, 
            "area": "PlayArea",
            "isActive": True,
            "card": {
            }
        },
        {
            "cardId": "EX1_625t", 
            "type": "HERO_POWER",
            "attack": 2, 
            "hp": 1, 
            "entityId": "3", 
            "playedRound": -1, 
            "area": "HandArea",
            "isActive": True,
            "card": {
            },
            "cost": 2,
        },
        {
            "cardId": "NX2_019", 
            "type": "SPELL",
            "attack": 2, 
            "hp": 1, 
            "entityId": "4", 
            "playedRound": -1, 
            "area": "HandArea",
            "isActive": True,
            "card": {
            },
            "cost": 1,
        },
        {
            "cardId": "NX2_019", 
            "type": "SPELL",
            "attack": 2, 
            "hp": 1, 
            "entityId": "5", 
            "playedRound": -1, 
            "area": "HandArea",
            "isActive": True,
            "card": {
            },
            "cost": 1,
        }
    ]

    rivalCardDetails = [
        {
            "type": "MINION",
            "cardId": "GDB_320", # GDB_320: 69.4, CFM_652: 69.4
            "attack": 4, 
            "hp": 5, 
            "entityId": "6", 
            "playedRound": -1, 
            "area": "PlayArea",
            "isActive": True,
            "card": {
                "isTaunt": True,
                "isLifesteal": True,
            }
        },
        {
            "type": "HERO",
            "cardId": "HERO_09", 
            "attack": 0, 
            "hp": 29,
            "area": "PlayArea",
            "entityId": "10", 
            "isActive": True,
            "playedRound": -1,
            "card": {
                "isImmune": False, 
                "isActive": False,
                "isDivineShield": False, # True: 14, False: 20
            },
            "debuff": 2
        },
        {
            "type": "MINION",
            "cardId": "SW_446", 
            "attack": 1, 
            "hp": 5, 
            "entityId": "7", 
            "playedRound": -1, 
            "area": "PlayArea",
            "isActive": True,
            "card": {
            },
            "cost": 2
        }
    ]

    for card in meCardDetails + rivalCardDetails:
        card["card_weight"] = getCoreCard([card["cardId"]])[card["cardId"]] + 1.0
    my_cards = [SimulateCard(card) for card in meCardDetails]
    rival_cards = [SimulateCard(card) for card in rivalCardDetails]

    print ("CARDS before start")
    for card in my_cards:
        print (card)
    for card in rival_cards:
        print (card)
    result = calc_clean(my_cards, rival_cards)
    rivalHero = [card for card in rivalCardDetails if card["type"] == "HERO"][0]
    for action in result.actions:
        print (action)
    print (f"times: {result.times}, rivalHP: {result.heroHP}, reduceHP: {rivalHero['hp'] - result.heroHP}, weight: {result.all_weight} ")

    for attack in result.actions:
        companion = attack.my_card.cardDetails
        rival = attack.rival_card.cardDetails
        if rival != None:
            print (f"{companion['cardId']} - {rival['cardId']} ({companion['entityId']} - {rival['entityId']}) ({HearthStoneById[companion['cardId']]['name']} - {HearthStoneById[rival['cardId']]['name']})")
        else:
            print (f"{companion['cardId']} - ({companion['entityId']} - ) ({HearthStoneById[companion['entityId']]['name']} - )")

case2()