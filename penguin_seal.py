"""
penguin_seal.py
---------------
담당: 1202 김산하

- Penguin : 크릴과 북극대구를 먹는 중간 포식자. 무리 생활.
- Seal    : 북극대구를 주로 먹고 크릴도 먹는 반수생 포식자. 곰/범고래의 먹이.
둘 다 빙판과 바다를 오갈 수 있는 반수생(HABITAT="any").
"""

import random
from animal import Animal


class Penguin(Animal):
    """펭귄 — 크릴/대구 포식, 무리 생활."""

    SPECIES = "Penguin"
    HABITAT = "any"
    CARRYING_CAPACITY = 38
    MATURITY = 10
    REPRO_COOLDOWN = 18
    BASE_REPRO_CHANCE = 0.6
    METABOLISM = 4
    WELLFED_HUNGER = 55
    DETECTION = 15.0
    LIFESPAN = 360
    TEMP_TOLERANCE = 5.0

    PREY = ("ArcticCod",)
    EATS_KRILL = True
    HUNT_SUCCESS = 0.45
    EAT_GAIN = 30.0                # 대구를 먹었을 때
    KRILL_TAKE = 12.0
    KRILL_GAIN = 15.0             # 크릴을 먹었을 때

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=50, speed=1.1, cold_resistance=0.85, **kw)


class Seal(Animal):
    """바다표범 — 대구 위주, 크릴 보조. 곰/범고래의 먹이."""

    SPECIES = "Seal"
    HABITAT = "any"
    CARRYING_CAPACITY = 22
    MATURITY = 14
    REPRO_COOLDOWN = 26
    BASE_REPRO_CHANCE = 0.55
    METABOLISM = 1.25
    WELLFED_HUNGER = 58
    DETECTION = 16.0
    LIFESPAN = 500
    TEMP_TOLERANCE = 7.0

    PREY = ("ArcticCod",)
    EATS_KRILL = True
    HUNT_SUCCESS = 0.6
    EAT_GAIN = 46.0
    KRILL_TAKE = 14.0
    KRILL_GAIN = 24.0

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=80, speed=1.15, cold_resistance=0.8,
                         hunger=25, **kw)
