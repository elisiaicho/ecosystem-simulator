"""
orca_cod.py
-----------
담당: 1212 이도윤

- Orca      : 해양 최상위 포식자. 물범/펭귄/대구를 먹는다. 느리게 번식.
- ArcticCod : 크릴을 먹는 1차 소비자. 떼지어 다니며, 포식 압력이 크므로
              빠르게(무성) 번식해 회복력이 높다.
"""

import random
from animal import Animal


class ArcticCod(Animal):
    """북극대구 — 크릴 포식, 무성생식, 높은 회복력."""

    SPECIES = "ArcticCod"
    HABITAT = "water"
    SEXUAL = False
    CARRYING_CAPACITY = 80
    MATURITY = 4
    REPRO_COOLDOWN = 5
    BASE_REPRO_CHANCE = 0.85       # 많이 먹히므로 번식이 빨라야 사슬 유지
    METABOLISM = 1.3
    WELLFED_HUNGER = 60
    DETECTION = 16.0
    LIFESPAN = 220
    TEMP_TOLERANCE = 4.0           # 부동액 혈액, 극저온 적응 → 수온에 가장 민감

    EATS_KRILL = True
    EAT_GAIN = 34.0                # 크릴을 먹었을 때 굶주림 감소
    KRILL_TAKE = 14.0              # 크릴 바이오매스에서 소모하는 양

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=20, speed=1.0, cold_resistance=0.95, **kw)
    def schooling_bias(self):
        return round(max(0.0, self.DETECTION - self.hunger * 0.05), 3)


class Orca(Animal):
    """범고래 — 해양 최상위 포식자."""

    SPECIES = "Orca"
    HABITAT = "water"
    CARRYING_CAPACITY = 8    # 10→8: 물범 과포식 방지
    MATURITY = 18
    REPRO_COOLDOWN = 28
    BASE_REPRO_CHANCE = 0.55
    METABOLISM = 0.95              # 큰 먹이를 가끔 먹고 오래 버팀
    WELLFED_HUNGER = 60
    DETECTION = 26.0
    LIFESPAN = 1200
    TEMP_TOLERANCE = 8.0

    PREY = ("Seal", "Penguin", "ArcticCod")
    HUNT_SUCCESS = 0.6
    EAT_GAIN = 70.0

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=250, speed=1.4, cold_resistance=0.85,
                         hunger=25, **kw)
        self.echo_ring =0
    def pod_signal_strength(self):
        return round(self.DETECTION + getattr(self, "echo_ring", 0) * 0.1, 3)
