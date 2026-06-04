"""
animal.py
---------
모든 극지방 동물의 공통 부모 클래스 Animal.
담당: 1210 이강희

[안정적인 생태계를 위한 핵심 설계]
이 시뮬레이션이 '전멸 + 크릴 폭증'으로 끝나지 않도록 3가지생태학 원리를
모든 종에 공통으로 적용한다.

1) 밀도의존 번식 확률 조정
   - 같은 종 개체수 N 이 환경수용력 K 에 가까울수록 번식 확률이 0 으로 줄고,
     N 이 적을수록 번식 확률이 커진다. 이를 통해, 폭증 방지 + 저밀도 회복 보장.
   - 번식 확률이 (1 - N/K)에 대해 선형적으로 감소하도록 한다.

2) hunger의 조정
   - hunger 0=배부름, 100=완전 굶주림. 매 턴 metabolism 만큼 증가.
   - 먹으면 감소. 100 도달 시 hp 감소(아사하게 됨). hp 0 → 사망함.
   - 잘 먹은 개체만(hunger < WELLFED_HUNGER) 번식 → 먹이가 부족하면 자연히
     번식이 멈추고 개체수가 줄어들게 만든다.

3) 성숙/번식 쿨다운/수명 지정해, 번식 매케니즘 조정
   - 1.갓 태어난 개체는 바로 번식 못 함(MATURITY).
   - 2.번식 후 쿨다운(REPRO_COOLDOWN) 동안 못 함.
   - 3.일부 종은 수명(LIFESPAN)이 있어 노화로 자연사 → 생태계 구현을 돕기

좌표 (x, y) 는 float. y < sea_line = 빙판, y >= sea_line = 바다.
"""

import math
import random




class Animal:
    """모든 극지방 동물의 공통 부모."""

    # 종별로 덮어쓰는 클래스 변수(종 특성) 
    SPECIES = "Animal"
    HABITAT = "any"           # "ice","water" ,"any"
    CARRYING_CAPACITY = 30    # 환경수용력 (밀도의존 번식의 기준), K로 표기함.
    MATURITY = 8              # 성숙까지 턴 수                         번식 1
    REPRO_COOLDOWN = 18       # 번식 간 최소 턴 수                     번식 2
    LITTER = 1                # 1회 번식당 새끼 수                     번식 3
    BASE_REPRO_CHANCE = 0.5   # K 대비 여유가 충분할 때의 기본 번식 확률  번식 4
    CHILD_INITIAL_HUNGER = 40 # 번식 5, 낳은 아이의 초기 허기
    METABOLISM = 4.0          # 매 턴 hunger 증가량                   hunger 1
    WELLFED_HUNGER = 45       # 이 값보다 배가 차 있어야 번식 가능       hunger 2
    FEED_HUNGER = 35          # 이 값보다 굶주려야 사냥/먹기 시작        hunger 3
    STARVE_DAMAGE = 10.0       # hunger 100 일 때 매 턴 잃는 hp        hunger 4
    DETECTION = 9.0           # 먹이/짝 탐지 반경
    LIFESPAN = None           # 최대 수명(턴). None 이면 노화사 없음
    SEXUAL = True             # True=암수 필요, False=무성생식
    # 기후(지구 온난화) 관련 ,  지구 온난화를 이용해 생태계가 끝나도록 함
    TEMP_TOLERANCE = 10.0      # 이 온도 초과 시 열 스트레스(해양종=수온, 육상종=공기온도)
    THERMAL_K = 2          # 내성 초과 1도당 매 턴 피해
    ICE_LOSS_DMG = 0.0        # 빙하 동물이 얼음 밖(녹은 바다)에 있을 때 매 턴 피해

    # 생성자 
    def __init__(self, x, y, hp, speed, cold_resistance,
                 gender=None, hunger=30):
        self.x = float(x)
        self.y = float(y)
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.speed = float(speed)
        self.cold_resistance = float(cold_resistance)
        self.gender = gender or random.choice(["M", "F"])
        self.hunger = float(hunger)
        self.is_alive = True
        self.age = 0
        # 시작 시 쿨다운을 흩뿌려 번식이 한꺼번에 몰리지 않게 함
        self.repro_cd = random.randint(0, self.REPRO_COOLDOWN)
        self.state = "idle"        # idle / hunting / fleeing / eating
        self.facing = 1            # 스프라이트 좌우 반전용
    
    # hp 프로퍼티
    @property
    def hp(self):
        return self.__hp
    @hp.setter
    def hp(self, value : float):
        self.__hp = max(0.0, min(100.0,float(value)))
        if self.__hp == 0 and self.is_alive:
            self.die()

    # hunger 프로퍼티
    @property
    def hunger(self):
        return self.__hunger
    @hunger.setter
    def hunger(self, value:float):
        self.__hunger = max(0.0, min(200.0, float(value)))
        if self.__hunger >= 200 and self.is_alive:
            self.hp = 0
    
    # 매 턴 갱신: 나이/굶주림/노화/아사 
    def update(self):
        if not self.is_alive:
            return
        self.age += 1
        if self.repro_cd > 0:
            self.repro_cd -= 1

        # 굶주림 증가
        self.hunger = min(100.0, self.hunger + self.METABOLISM)

        # 아사 피해
        if self.hunger >= 100.0:
            self.take_damage(self.STARVE_DAMAGE)

        # 노화사
        if self.LIFESPAN is not None and self.age > self.LIFESPAN:
            self.take_damage(self.STARVE_DAMAGE * 15)  # 수명 끝에서 갑자기가 아니라 서서히 약해지도록
        # animal 들의 물 감속 속도 구현하기.
        speed_decrease_rate = getattr(self, 'water_speed_decreasingrate', 0)
        
    # 먹기: 굶주림 감소 + 약간의 체력 회복 
    def eat(self, amount):
        if not self.is_alive:
            return
        self.hunger = max(0.0, self.hunger - amount)
        self.hp = min(self.max_hp, self.hp + amount * 0.25)
        self.state = "eating"

    # 피해/사망 
    def take_damage(self, dmg):
        if not self.is_alive:
            return
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.die()

    def die(self):
        self.is_alive = False
        self.state = "dead"

    # 번식 가능 여부(밀도의존) 
    def can_reproduce(self, species_count):
        """
        번식 가능하면 번식 '확률'을 반환, 불가하면 0.0.

        species_count: 현재 살아있는 같은 종 개체수 N.
        확률 = BASE_REPRO_CHANCE * (1 - N/K)   (N>=K 이면 0)
        """
        if not self.is_alive:
            return 0.0
        if self.age < self.MATURITY:
            return 0.0
        if self.repro_cd > 0:
            return 0.0
        if self.hunger > self.WELLFED_HUNGER:
            return 0.0
        K = self.CARRYING_CAPACITY
        if species_count >= K:
            return 0.0
        # 로지스틱: 여유가 많을수록 번식 확률 ↑
        room = 1.0 - (species_count / K)
        return self.BASE_REPRO_CHANCE * room

    def reset_repro(self):
        """번식 직후 쿨다운/굶주림 비용 부과."""
        self.repro_cd = self.REPRO_COOLDOWN
        # 번식은 허기를 쓴다 → 굶주림 증가(과번식 자기억제)
        self.hunger = min(100.0, self.hunger + 20.0)

    def make_offspring(self, x, y):
        """새끼 1마리 생성. 자식 클래스가 동일 타입을 반환하도록 사용."""
        child = type(self)(x=x, y=y)
        child.hunger = self.CHILD_INITIAL_HUNGER
        return child

    # 이동 헬퍼
    def get_distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    def _step(self, dx, dy, world_w, world_h):
        d = math.hypot(dx, dy)
        if d > 1e-9:
            self.x += (dx / d) * self.speed
            self.y += (dy / d) * self.speed
            self.facing = 1 if dx >= 0 else -1
        self._clamp(world_w, world_h)

    def move_toward(self, tx, ty, world_w, world_h):
        self._step(tx - self.x, ty - self.y, world_w, world_h)

    def move_away(self, tx, ty, world_w, world_h):
        self._step(self.x - tx, self.y - ty, world_w, world_h)

    def random_walk(self, world_w, world_h):
        self._step(random.uniform(-1, 1), random.uniform(-1, 1),
                   world_w, world_h)

    def _clamp(self, world_w, world_h, sea_line=None):
        """월드 밖으로 못 나가게. 서식지(빙판/바다)도 강제."""
        self.x = min(max(self.x, 0.0), world_w - 1)
        self.y = min(max(self.y, 0.0), world_h - 1)
        if sea_line is None:
            return
        if self.HABITAT == "ice" and self.y >= sea_line:
            self.y = sea_line - 1
        elif self.HABITAT == "water" and self.y < sea_line:
            self.y = sea_line + 1

    def __repr__(self):
        s = "alive" if self.is_alive else "dead"
        return (f"<{self.SPECIES} ({self.x:.0f},{self.y:.0f}) "
                f"hp={self.hp:.0f} hun={self.hunger:.0f} {s}>")