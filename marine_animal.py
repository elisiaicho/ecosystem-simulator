import random
from animal import Animal 
# animal.py 에서 Animal 클래스를 import 한다고 가정
# from animal import Animal
 
TEMP_TOLERANCE = 5          # 최적 온도에서 ±5도까지는 피해 없음
TEMP_DMG_PER_DEGREE = 1     # 허용 범위를 벗어난 1도당 hp 피해량
 
OXYGEN_DECREASE_RATE = 5    # 매 턴 수중에서 소모되는 산소량
OXYGEN_RECOVER_RATE  = 20   # 수면 위에서 매 턴 회복되는 산소량
 
class MarineAnimal(Animal):
    def __init__(self, hp, age, max_age, speed, hunger, x, y,
                 cold_resistance, gender, gestation, prey_types, hunting_range,
                 attack, defense,
                 # MarineAnimal 고유 속성
                 max_oxygen, optimum_watertemp, krill_intake):
        
        super().__init__(hp, age, max_age, speed, hunger, x, y,
                         cold_resistance, gender, gestation, prey_types,
                         hunting_range, attack, defense)
 
        self.max_oxygen       = max_oxygen          # 최대 산소량
        self.oxygen           = max_oxygen          # 현재 산소량 (처음엔 가득 찬 상태)
        self.optimum_watertemp = optimum_watertemp  # 최적 수온 (°C)
        self.krill_intake     = krill_intake        # 한 번에 크릴을 먹을 때 hunger가 감소하는 양
        self.is_underwater    = True                # 현재 수중 여부
 
    # ── 온도 피해 ──────────────────────────────────────────────────
    def temp_dmg(self, temp):
        """
        현재 수온(temp)이 최적 온도(optimum_watertemp)에서
        ±TEMP_TOLERANCE 를 벗어날수록 hp 피해가 선형으로 증가한다.
 
        허용 범위: [optimum_watertemp - 5, optimum_watertemp + 5]
        벗어난 도수(degree) 1도당 TEMP_DMG_PER_DEGREE 만큼 피해.
        """
        deviation = abs(temp - self.optimum_watertemp)
        excess    = deviation - TEMP_TOLERANCE      # 허용 범위를 초과한 정도
 
        if excess > 0:
            damage = excess * TEMP_DMG_PER_DEGREE
            self.hp -= damage
            print(f"{self.name}이(가) 수온 {temp}°C 로 {damage:.1f}의 온도 피해를 받았다. "
                  f"(최적:{self.optimum_watertemp}°C, 허용범위: ±{TEMP_TOLERANCE}°C)")
        else:
            pass    # 허용 범위 내이므로 피해 없음
 
    # ── 크릴 섭취 ──────────────────────────────────────────────────
    def eat_krill(self, krill_swarm):
        """
        krill_swarm: Krill 객체(무한히 증식하는 자원).
        krill_swarm 에서 크릴을 먹어 hunger 를 krill_intake 만큼 낮춘다.
        Krill 의 swarm_size 는 1 감소한다.
        """
        if krill_swarm is None or not krill_swarm.is_alive:
            print(f"{self.name}: 먹을 크릴이 없습니다.")
            return
 
        self.hunger = max(0, self.hunger - self.krill_intake)
        krill_swarm.swarm_size = max(0, krill_swarm.swarm_size - 1)
        print(f"{self.name}이(가) 크릴을 먹었다. "
              f"hunger: {self.hunger}, 크릴 swarm_size: {krill_swarm.swarm_size}")
 
    # ── 무작위 수영 이동 ───────────────────────────────────────────
    def random_swim(self, box_size=None):
        """
        현재 위치(x, y) 기준으로 box_size × box_size 박스 안에서 무작위 이동한다.
        box_size 를 따로 지정하지 않으면 speed 를 기본값으로 사용한다.
 
        이동 후 위치:
            x ∈ [현재x - box_size/2,  현재x + box_size/2]
            y ∈ [현재y - box_size/2,  현재y + box_size/2]
        """
        if not self.is_alive:
            return
 
        half = (box_size if box_size is not None else self.speed) / 2
        self.x += random.uniform(-half, half)
        self.y += random.uniform(-half, half)
        print(f"{self.name}이(가) 근처를 배회했다. → ({self.x:.1f}, {self.y:.1f})")
 
    # ── 다른 동물을 향한 수중 이동 ────────────────────────────────
    def move_toward(self, target):
        """
        target 동물 방향으로 speed 만큼 이동한다.
        target 까지 거리가 speed 보다 짧으면 target 위치로 바로 이동한다.
        (사냥감 추적, 무리 합류 등에 사용)
        """
        if not self.is_alive:
            return
 
        dist = self.get_distance(target)
        if dist == 0:
            return
 
        # 단위 벡터 × min(speed, 남은거리) → 목표를 넘어서지 않음
        ratio  = min(self.speed, dist) / dist
        self.x += (target.x - self.x) * ratio
        self.y += (target.y - self.y) * ratio
        print(f"{self.name}이(가) {target.name}을(를) 따라 이동했다. → ({self.x:.1f}, {self.y:.1f})")
 
    # ── 산소 관리 (수중/수면 전환) ────────────────────────────────
    def use_oxygen(self):
        """수중에 있을 때 매 턴 산소를 소모한다. 0이 되면 hp 피해."""
        self.oxygen = max(0, self.oxygen - OXYGEN_DECREASE_RATE)
        if self.oxygen == 0:
            self.hp -= 10
            print(f"{self.name}이(가) 산소 부족으로 피해를 받았다!")
 
    def recover_oxygen(self):
        """수면 위(is_underwater=False)일 때 매 턴 산소를 회복한다."""
        self.oxygen = min(self.max_oxygen, self.oxygen + OXYGEN_RECOVER_RATE)
 
    # ── update 오버라이딩 ──────────────────────────────────────────
    def update(self, current_temp=None):
        """
        Animal.update() 를 호출한 뒤 MarineAnimal 고유 로직을 추가한다.
        current_temp: 이번 턴의 수온. None 이면 온도 피해 없음.
        """
        super().update()
 
        if not self.is_alive:
            return
 
        # 산소 처리
        if self.is_underwater:
            self.use_oxygen()
        else:
            self.recover_oxygen()
 
        # 수온 피해
        if current_temp is not None:
            self.temp_dmg(current_temp)
