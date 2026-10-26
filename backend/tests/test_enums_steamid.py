from app.gamedata.enums import objective_parts, parse_enums
from app.gamedata.steamid import parse_account_id

PROTO = """
enum ECitadelTeamObjective {
	k_eCitadelTeamObjective_Core = 0;
	k_eCitadelTeamObjective_Tier1_Lane1 = 1;
	k_eCitadelTeamObjective_Tier2_Lane3 = 7;
	k_eCitadelTeamObjective_TitanShieldGenerator_2 = 11;
	k_eCitadelTeamObjective_BarrackBoss_Lane4 = 15;
}
message CMsgMatchMetaDataContents {
	enum ECombatType {
		k_eCombatType_Out = 0;
		k_eCombatType_Player = 1;
	}
	enum EGoldSource {
		k_ePlayers = 1;
		k_eLaneCreeps = 2;
	}
}
enum Unrelated { k_eX = 1; }
"""


def test_parse_enums_strips_prefixes():
    e = parse_enums(PROTO)
    assert e["ECitadelTeamObjective"]["0"] == "Core"
    assert e["ECitadelTeamObjective"]["7"] == "Tier2_Lane3"
    assert e["ECombatType"] == {"0": "Out", "1": "Player"}
    assert e["EGoldSource"]["2"] == "LaneCreeps"
    assert "Unrelated" not in e


def test_objective_parts():
    assert objective_parts("Tier1_Lane1") == {"kind": "tier1", "lane": 1, "index": None}
    assert objective_parts("TitanShieldGenerator_2") == {"kind": "shrine", "lane": None, "index": 2}
    assert objective_parts("BarrackBoss_Lane4")["kind"] == "barracks"
    assert objective_parts("Titan")["kind"] == "titan"
    assert objective_parts("Core")["kind"] == "core"


def test_parse_account_id_formats():
    assert parse_account_id("76561198000000000") == 39734272
    assert parse_account_id("[U:1:123]") == 123
    assert parse_account_id("U:1:123") == 123
    assert parse_account_id("STEAM_0:1:10") == 21
    assert parse_account_id("https://steamcommunity.com/profiles/76561198000000000/") == 39734272
    assert parse_account_id("123456") == 123456
    assert parse_account_id("not an id") is None
    assert parse_account_id("") is None
