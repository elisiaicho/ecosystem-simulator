"""
krill_reindeer.py
-----------------
생산자/초식동물
담당: 1216 홍주영

- Krill    : 바다 먹이사슬 최하층. '떼(swarm)' 객체로 표현하되, 폭증을 막기 위해
             전체 크릴 '바이오매스'를 로지스틱 성장으로 상한(KRILL_CAP)에 묶는다.
             (성장은 Simulation 이 전체 바이오매스 기준으로 분배 → 한 개체의
              swarm_size 가 복리로 무한히 부푸는 옛 버그를 원천 차단)
- Reindeer : 빙판/툰드라에서 '이끼(lichen, 재생 자원)'를 먹는다. 이끼가 부족하면
             번식이 줄어 순록도 늘지 못한다(자원 상한).
"""

import random
from animal import Animal


class Krill(Animal):
    """크릴 떼 — 무성생식. 전체 바이오매스는 Simulation 이 로지스틱으로 관리."""

    SPECIES = "Krill"
    HABITAT = "water"
    SEXUAL = False
    # 크릴은 개체수가 아니라 '바이오매스'로 상한이 걸리므로 K 는 객체 수 상한용
    CARRYING_CAPACITY = 45        # 화면에 흩어놓을 크릴 떼 객체 최대 개수
    METABOLISM = 0.0              # 크릴은 굶지 않음(플랑크톤을 먹는 1차 생산 가정)
    LIFESPAN = None
    TEMP_TOLERANCE = 12.0          # 가장 내열성↑ → 마지막까지 생존(멸망 기준종)

    # 바이오매스 동역학 상수(Simulation 이 사용)
    BIOMASS_CAP = 6000.0          # 전체 크릴 바이오매스 환경수용력
    GROWTH_R = 0.28               # 로지스틱 성장률
    PER_OBJ_MAX = 400.0           # 떼 객체 하나가 가질 수 있는 최대 swarm_size
    PER_OBJ_START = 150.0

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=5, speed=0.4, cold_resistance=1.0,
                         hunger=0, **kw)
        self.swarm_size = self.PER_OBJ_START

    def update(self):
        # 크릴은 굶주림/노화 로직 없이 살아만 있음(성장은 sim 이 처리)
        if self.is_alive:
            self.age += 1
            if self.swarm_size <= 0:
                self.die()

    def drift(self, world_w, world_h, sea_line):
        if not self.is_alive:
            return
        self.x += random.uniform(-0.4, 0.4)
        self.y += random.uniform(-0.4, 0.4)
        self._clamp(world_w, world_h, sea_line)

    def grazed(self, amount):
        """포식자가 크릴을 먹을 때 호출 — 떼 크기 감소, 실제로 먹힌 양 반환."""
        eaten = min(self.swarm_size, amount)
        self.swarm_size -= eaten
        if self.swarm_size <= 0:
            self.die()
        return eaten


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
    ICE_LOSS_DMG = 14.0            # 빙하/툰드라가 녹으면 갈 곳이 없다(헤엄 못 침)

    # 먹이 = 이끼
    EATS_LICHEN = True
    GRAZE_GAIN = 26.0             # 한 번 풀을 뜯을 때 굶주림 감소량
    GRAZE_COST = 9.0             # 이끼 자원에서 소모하는 양

    def __init__(self, x=0, y=0, **kw):
        super().__init__(x=x, y=y, hp=90, speed=1.3, cold_resistance=0.78, **kw)
        self.herd_size = 1
