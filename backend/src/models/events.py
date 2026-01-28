"""Game event models (kills, bombs, grenades)."""

from enum import Enum

from pydantic import BaseModel


class WeaponCategory(str, Enum):
    """Weapon categories."""

    PISTOL = "pistol"
    SMG = "smg"
    RIFLE = "rifle"
    SNIPER = "sniper"
    SHOTGUN = "shotgun"
    MACHINE_GUN = "machine_gun"
    KNIFE = "knife"
    GRENADE = "grenade"
    OTHER = "other"


class Kill(BaseModel):
    """A kill event."""

    tick: int
    round_num: int

    # Attacker info
    attacker_steamid: str | None = None  # None for world damage (fall, bomb)
    attacker_name: str | None = None
    attacker_team: str | None = None
    attacker_x: float | None = None
    attacker_y: float | None = None
    attacker_z: float | None = None

    # Victim info
    victim_steamid: str
    victim_name: str
    victim_team: str
    victim_x: float
    victim_y: float
    victim_z: float

    # Kill details
    weapon: str
    headshot: bool = False
    penetrated: bool = False  # Wallbang
    noscope: bool = False
    thrusmoke: bool = False
    attackerblind: bool = False

    # Assist info
    assister_steamid: str | None = None
    assister_name: str | None = None
    flash_assist: bool = False

    # Computed
    is_trade: bool = False  # Set by analysis
    trade_window_ticks: int | None = None


class BombEvent(BaseModel):
    """Bomb-related event (plant, defuse, explode)."""

    tick: int
    round_num: int
    event_type: str  # "plant", "defuse", "explode", "drop", "pickup"

    player_steamid: str | None = None
    player_name: str | None = None

    # Position (for plant/explode)
    x: float | None = None
    y: float | None = None
    z: float | None = None

    # Site (for plant)
    site: str | None = None  # "A" or "B"


class GrenadeEvent(BaseModel):
    """Grenade usage event."""

    tick: int
    round_num: int

    thrower_steamid: str
    thrower_name: str
    thrower_team: str

    grenade_type: str  # "smoke", "flashbang", "hegrenade", "molotov", "incendiary", "decoy"

    # Throw position
    throw_x: float
    throw_y: float
    throw_z: float

    # Detonate position
    detonate_x: float | None = None
    detonate_y: float | None = None
    detonate_z: float | None = None

    # Flash-specific
    players_flashed: list[str] = []  # steamids of flashed players
    enemies_flashed: int = 0


class DamageEvent(BaseModel):
    """Damage dealt event."""

    tick: int
    round_num: int

    attacker_steamid: str | None = None
    attacker_name: str | None = None
    attacker_team: str | None = None

    victim_steamid: str
    victim_name: str
    victim_team: str

    weapon: str
    damage: int
    damage_armor: int = 0
    health_remaining: int
    armor_remaining: int
    hitgroup: str = "generic"  # head, chest, stomach, left_arm, right_arm, left_leg, right_leg
