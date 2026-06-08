"""
krill_reindeer.py
-----------------
크릴(Krill), 순록(Reindeer)
담당: 1216 홍주영
"""
import random
import math
from animal import Animal


class Krill(Animal):
    """
    크릴은 개체가 아닌 '떼(swarm)' 단위로 관리된다.
    swarm_size: 떼의 바이오매스(float).
    main.py의 _update_krill이 로지스틱 성장을 직접 처리하므로
    update()는 최소한의 처리만 한다.
    """
    SPECIES           = "Krill"
    HABITAT           = "water"
    CARRYING_CAPACITY = 60   # 떼 객체 수 상한
    MATURITY          = 0
    REPRO_COOLDOWN    = 0
    LITTER            = 0
    BASE_REPRO_CHANCE = 0.0
    METABOLISM        = 0.0   # main._update_krill이 바이오매스로 처리
    WELLFED_HUNGER    = 100
    FEED_HUNGER       = 100
    STARVE_DAMAGE     = 0.0
    DETECTION         = 0.0
    LIFESPAN          = None
    SEXUAL            = False
    TEMP_TOLERANCE    = 5.0
    THERMAL_K         = 2.0
    ICE_LOSS_DMG      = 0.0
    # 크릴 바이오매스 상수 (main.py에서 직접 참조)
    BIOMASS_CAP       = 3000.0
    GROWTH_R          = 0.08
    PER_OBJ_MAX       = 120.0
    PER_OBJ_START     = 50.0
    DRIFT_SPEED       = 0.8

    def __init__(self, x=0, y=0, **kwargs):
        kwargs.setdefault("hp", 100)
        kwargs.setdefault("speed", self.DRIFT_SPEED)
        kwargs.setdefault("cold_resistance", 0.6)
        kwargs.setdefault("hunger", 0)
        super().__init__(x=x, y=y, **kwargs)
        self.swarm_size = self.PER_OBJ_START

    def update(self):
        """크릴은 main._update_krill이 관리하므로 굶주림/아사 로직 생략."""
        if not self.is_alive:
            return
        self.age += 1
        # 수온 스트레스는 main._apply_climate에서 처리

    def drift(self, world_w, world_h, sea_line, terrain=None):
        """해류를 따라 무작위 표류. terrain이 있으면 빙하 위 진입 방지."""
        import math as _math, random as _rand
        # 이미 빙하 위에 있으면 우선 빠져나오기 시도 (최대 8방향)
        if terrain is not None and terrain.is_ice_at(self.x, self.y):
            for _ in range(8):
                angle = _rand.uniform(0, 2 * _math.pi)
                nx = self.x + _math.cos(angle) * self.speed * 2
                ny = self.y + _math.sin(angle) * self.speed * 2
                nx = min(max(nx, 0.0), world_w - 1)
                ny = min(max(ny, 0.0), world_h - 1)
                if not terrain.is_ice_at(nx, ny):
                    self.x, self.y = nx, ny
                    return
            return  # 탈출 못하면 그 자리 유지

        # 정상 표류: 이동 후 빙하면 이전 위치 유지
        prev_x, prev_y = self.x, self.y
        angle = _rand.uniform(0, 2 * _math.pi)
        self.x += _math.cos(angle) * self.speed
        self.y += _math.sin(angle) * self.speed
        self._clamp(world_w, world_h)
        if terrain is not None and terrain.is_ice_at(self.x, self.y):
            self.x, self.y = prev_x, prev_y

    def grazed(self, amount):
        """포식자가 크릴을 먹을 때 호출. 실제로 먹힌 양 반환."""
        take = min(self.swarm_size, amount)
        self.swarm_size -= take
        if self.swarm_size <= 0:
            self.swarm_size = 0
            self.hp = 0   # 떼 소멸
        return take

    def give_birth(self):
        # 크릴 번식은 main._update_krill이 처리
        return None

    def can_reproduce(self, species_count=0):
        return 0.0


class Reindeer(Animal):
    """순록 — 무리 초식동물. 이끼(재생 자원)를 먹는다."""

    SPECIES = "Reindeer"
    HABITAT = "ice"
    CARRYING_CAPACITY = 28
    MATURITY = 12
    REPRO_COOLDOWN = 24
    BASE_REPRO_CHANCE = 0.55
    METABOLISM = 1.6
    WELLFED_HUNGER = 55
    DETECTION = 14.0
    LIFESPAN = 600
    TEMP_TOLERANCE = 6.0           # 공기온도 기준
    ICE_LOSS_DMG = 40.0            # 빙하/툰드라가 녹으면 갈 곳이 없다(헤엄 못 침)

    # 먹이 = 이끼
    EATS_LICHEN = True
    GRAZE_GAIN = 26.0             # 한 번 풀을 뜯을 때 굶주림 감소량
    GRAZE_COST = 9.0             # 이끼 자원에서 소모하는 양

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=90, speed=1.3, cold_resistance=0.78, **kw)
        self.herd_size = 1
        self.water_speed_decreasingrate = 0.6
    
    def herd_alertness(self):
        return round(self.herd_size + self.DETECTION * 0.1, 3)


