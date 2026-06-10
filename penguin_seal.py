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
    REPRO_COOLDOWN = 15
    BASE_REPRO_CHANCE = 0.72
    METABOLISM = 0.6          # 1 → 0.6: 굶주림 증가 속도 완화로 수명 연장
    WELLFED_HUNGER = 68
    DETECTION = 30.0
    LIFESPAN = 720            # 360 → 720: 실제 펭귄 수명(20년)에 맞게 2배 연장
    TEMP_TOLERANCE = 5.0
    STARVE_DAMAGE = 5.0 #오버라이드
    PREY = ("ArcticCod",)
    EATS_KRILL = True
    HUNT_SUCCESS = 0.45
    EAT_GAIN = 30.0                # 대구를 먹었을 때
    KRILL_TAKE = 12.0
    KRILL_GAIN = 15.0             # 크릴을 먹었을 때

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=50, speed=1.1, cold_resistance=0.85, **kw)
        if random.random() < 0.1:
            self.shiny_variant = random.choice([0,1])
            # 이로치 버프
            self.max_hp *= 1.2
            self.hp = self.max_hp
            self.EAT_GAIN *= 1.2
            self.KRILL_GAIN *= 1.2
            self.HUNT_SUCCESS += 0.20
        else:
            self.shiny_variant =None
        
    
    
    def huddle_score(self):
        """0~1. 배부르고 추위에 강할수록 높음."""
        return round((1.0 - min(self.hunger, 100.0) / 100.0) * self.cold_resistance, 3)

    def can_reproduce(self, species_count):
        """부모 확률에 huddle_score 보너스(최대 +0.15) 추가."""
        base = super().can_reproduce(species_count)
        if base <= 0:
            return 0.0
        # 무리 밀집 효과: huddle이 높을수록 번식 확률 최대 30% 증폭
        bonus = self.huddle_score() * 0.30
        return min(base * (1.0 + bonus), 1.0)

    def can_reproduce_here(self, terrain):
        return terrain.is_ice_at(self.x, self.y)

    def choose_offspring_position(self, terrain):
        if terrain.is_ice_at(self.x, self.y):
            return self.x + random.uniform(-1.5, 1.5), self.y + random.uniform(-1.5, 1.5)
        ice = terrain.nearest_ice(self.x, self.y)
        if ice is not None:
            return ice
        return self.x, self.y

    def update(self):
        """huddle 효과: 배부른 펭귄은 추위 피해를 조금 덜 받는다."""
        super().update()
        if not self.is_alive:
            return
        hs = self.huddle_score()
        # huddle이 높으면 추위 피해 경감 (체력을 미세하게 회복)
        if hs > 0.5:
            self.hp = min(self.max_hp, self.hp + (hs - 0.5) * 0.4)

class Seal(Animal):
    """바다표범 — 대구 위주, 크릴 보조. 곰/범고래의 먹이."""

    SPECIES = "Seal"
    HABITAT = "any"
    CARRYING_CAPACITY = 32
    MATURITY = 12            # 14→12
    REPRO_COOLDOWN = 18      # 20→18
    BASE_REPRO_CHANCE = 0.65 # 0.62→0.65
    LITTER = 1               # 명시적으로 유지
    METABOLISM = 1.25
    WELLFED_HUNGER = 62      # 58→62: 번식 허용 범위 넓힘
    DETECTION = 28.0
    LIFESPAN = 500
    TEMP_TOLERANCE = 7.0

    PREY = ("ArcticCod",)
    EATS_KRILL = True
    HUNT_SUCCESS = 0.55      # 0.6→0.55
    EAT_GAIN = 46.0
    KRILL_TAKE = 14.0
    KRILL_GAIN = 24.0

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=80, speed=1.15, cold_resistance=0.8,
                         hunger=25, **kw)
    def dive_readiness(self):
        health_ratio = self.hp / max(self.max_hp, 1.0)
        return round(health_ratio * self.cold_resistance, 3)
