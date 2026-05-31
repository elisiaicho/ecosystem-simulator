import random

from animal import Animal

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

        self.max_oxygen        = max_oxygen         # 최대 산소량
        self.oxygen            = max_oxygen         # 현재 산소량 (처음엔 가득 찬 상태)
        self.optimum_watertemp = optimum_watertemp  # 최적 수온 (°C)
        self.krill_intake      = krill_intake       # 크릴 1회 섭취 시 hunger 감소량
        self.is_underwater     = True               # 현재 수중 여부

    # ── 온도 피해 ──────────────────────────────────────────────────
    def temp_dmg(self, temp):
        """
        현재 수온(temp)이 optimum_watertemp 에서 ±5도를 벗어날수록
        hp 피해가 선형으로 증가한다.
        (main.py _apply_climate() 와 별개 — 직접 호출 용도로 남겨둠)
        """
        TOLERANCE = 5
        excess = abs(temp - self.optimum_watertemp) - TOLERANCE
        if excess > 0:
            self.hp -= excess
            print(f"{self.name}이(가) 수온 {temp}°C 로 {excess:.1f}의 온도 피해를 받았다.")

    # ── 크릴 섭취 ──────────────────────────────────────────────────
    def eat_krill(self, krill_swarm):
        """
        krill_swarm 에서 크릴을 먹어 hunger 를 krill_intake 만큼 낮춘다.
        Krill.swarm_size 를 1 감소시킨다.
        """
        if krill_swarm is None or not krill_swarm.is_alive:
            print(f"{self.name}: 먹을 크릴이 없습니다.")
            return

        self.hunger = max(0, self.hunger - self.krill_intake)
        krill_swarm.swarm_size = max(0, krill_swarm.swarm_size - 1)
        print(f"{self.name}이(가) 크릴을 먹었다. "
              f"hunger: {self.hunger}, 크릴 swarm_size: {krill_swarm.swarm_size}")

    # ── 이동 오버라이딩 ───────────────────────────────────────────
    # 육지(is_underwater=False): Animal 기본 구현 그대로 사용(super() 위임).
    # 바다(is_underwater=True) : 알고리즘은 동일하되 swim 동작으로 처리.
    # Penguin/Seal 처럼 HABITAT="any" 인 반수생 동물도 상태에 따라 자동 분기.

    def random_walk(self, world_w, world_h):
        """육지면 걷기, 바다면 수영 — 알고리즘은 동일."""
        if not self.is_alive:
            return
        if not self.is_underwater:
            super().random_walk(world_w, world_h)
            return
        # 바다: random_swim — Animal.random_walk 와 동일한 알고리즘
        self._step(random.uniform(-1, 1), random.uniform(-1, 1),
                   world_w, world_h)
        print(f"{self.name}이(가) 무작위로 수영했다. → ({self.x:.1f}, {self.y:.1f})")

    def move_toward(self, tx, ty, world_w, world_h):
        """육지면 걷기, 바다면 수영으로 목표 추적 — 알고리즘은 동일."""
        if not self.is_alive:
            return
        if not self.is_underwater:
            super().move_toward(tx, ty, world_w, world_h)
            return
        # 바다: swim_toward — Animal.move_toward 와 동일한 알고리즘
        self._step(tx - self.x, ty - self.y, world_w, world_h)
        print(f"{self.name}이(가) ({tx:.1f},{ty:.1f}) 방향으로 수영했다. "
              f"→ ({self.x:.1f}, {self.y:.1f})")

    # ── 산소 관리 ─────────────────────────────────────────────────
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
    # main.py 는 a.update() 를 인자 없이 호출한다.
    # 온도 피해는 _apply_climate() 에서 종별 TEMP_TOLERANCE 기준으로 처리하므로
    # 여기서 중복 계산하지 않는다. 산소 소모/회복만 추가한다.
    def update(self):
        """
        Animal.update() 호출 후 산소 소모/회복만 추가한다.
        온도 피해는 main.py _apply_climate() 가 담당하므로 여기서 처리하지 않는다.
        """
        super().update()

        if not self.is_alive:
            return

        if self.is_underwater:
            self.use_oxygen()
        else:
            self.recover_oxygen()
