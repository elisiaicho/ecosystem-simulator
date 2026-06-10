"""
land_predators.py
-----------------
담당: 1210 이강희

- PolarBear : 육상/빙판 최상위 포식자. 물범과 순록을 사냥. 느리게 번식.
- ArcticFox : 소형 먹이를 잡고, 곰/범고래가 남긴 '사체(carcass)'를 청소하는
              스캐빈저. 사체가 있으면 굶주림을 크게 던다.
"""

import random
from animal import Animal


class PolarBear(Animal):
    """북극곰 — 빙판 최상위 포식자."""

    SPECIES = "PolarBear"
    HABITAT = "ice"
    CARRYING_CAPACITY = 14    
    MATURITY = 18
    REPRO_COOLDOWN = 38
    BASE_REPRO_CHANCE = 0.52
    METABOLISM = 0.9
    WELLFED_HUNGER = 60
    DETECTION = 30.0
    LIFESPAN = 900
    TEMP_TOLERANCE = 5.0           # 공기온도 기준
    ICE_LOSS_DMG = 10.0             # 헤엄 능숙 → 피해 작음(단, 사냥터 상실)
    STARVE_DAMAGE = 5.0 # animal의 변수 오버라이드
    PREY = ("Seal", "Reindeer")
    HUNT_SUCCESS = 0.47      # 0.5→0.40: 물범·순록 사냥 약화로 포식압 완화
    EAT_GAIN = 62.0

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=200, speed=1.25, cold_resistance=0.95,
                         hunger=25, **kw)
    def ice_patrol_radius(self):
        return round(self.DETECTION + self.speed * 2.0, 3)


class ArcticFox(Animal):
    """북극여우 — 소형 먹이 + 사체 청소부."""

    SPECIES = "ArcticFox"
    HABITAT = "ice"
    CARRYING_CAPACITY = 18
    MATURITY = 8
    REPRO_COOLDOWN = 18
    BASE_REPRO_CHANCE = 0.55
    METABOLISM = 1.8
    WELLFED_HUNGER = 55
    DETECTION = 18.0
    LIFESPAN = 320
    TEMP_TOLERANCE = 7.0           # 공기온도 기준
    ICE_LOSS_DMG = 25.0
    STARVE_DAMAGE = 13.0            # 오버라이드
    # 여우는 작은 먹이(레밍 등, 추상화한 재생 자원 forage)와 사체로 산다.
    SCAVENGER = True
    FORAGE_GAIN = 18.0            # 작은 먹이를 잡았을 때(저강도, 항상 약간 가능)
    FORAGE_SUCCESS = 0.255
    CARCASS_GAIN = 40.0           # 사체를 먹었을 때

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=40, speed=1.4, cold_resistance=0.88, **kw)
    def foraging_efficiency(self):
        hunger_bonus = max(0.0, 50.0 - self.hunger) / 100.0
        return round(self.FORAGE_SUCCESS * (1.0 + hunger_bonus), 3)
