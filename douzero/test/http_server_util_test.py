from douzero.dmc.http_server_util import getCoreCard
from douzero.env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone, HearthStoneById, GameEnv

coreCards = getCoreCard(CardSet + ["CORE_EX1_012", "TOY_507", "TOY_528", "CFM_325", "SW_446", "MIS_710"])

for card in ["TOY_518", "VAC_512", "CORE_EX1_012", "DRG_056", "TOY_507", "TOY_528", "CFM_325", "SW_446", "MIS_710", "CFM_637", "CORE_WON_065"]:
    print (card, HearthStoneById[card]["name"], coreCards[card])
    print (HearthStoneById[card]["text"])