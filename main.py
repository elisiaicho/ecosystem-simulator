"""
main.py
-------
전체 코드 병합 및 시뮬레이션 루프
담당: 1210 이강희 (전체 코드 병합 담당)

[안정적인 생태계 유지 원리 — 루프 차원]
- 크릴(생산자급)은 '바이오매스 로지스틱 성장'으로 상한에 묶이고, 바닥 floor 가
  있어 절대 0 으로 사라지지 않는다(먹이사슬의 토대 보존).
- 이끼(순록 먹이)도 로지스틱 재생 자원이라 순록 수를 자연스럽게 제한한다.
- 모든 포식은 '탐지 → 접근 → 성공확률' 의 포화형(Holling) 방식이라, 먹이가
  적어지면 포식 효율도 떨어져 피식자가 0 까지 가지 않는다.
- 모든 번식은 밀도의존(로지스틱): 개체수가 K 에 가까우면 멈추고, 적으면
  되살아난다. → 폭증도 전멸도 막는 음의 되먹임.
- 사체(carcass)는 여우/곰의 먹이로 재활용되어 에너지가 순환한다.

종료 조건:
  - AI 무한질주에 의한 지구 온난화(바닷물 전량 증발) — 매 턴 0.00002*turn 확률
  - 사용자 ESC (pygame 모드)

실행:
  pip install pygame          # 시각화용(헤드리스는 불필요)
  python main.py              # pygame 시각화
  python main.py --headless 2000   # 화면 없이 2000턴 검증
"""

import math
import random
import sys

from animal import Animal
from land_predators import PolarBear, ArcticFox      # 1210 이강희
from penguin_seal import Penguin, Seal               # 1202 김산하
from orca_cod import Orca, ArcticCod                 # 1212 이도윤
from krill_reindeer import Krill, Reindeer           # 1216 홍주영
from ecosystem_events import (Blizzard, GlacierCollapse,
                              Starvation, AiBoilingApocalypse)
from terrain import Terrain
from viz_manager import VisualManager # 내가 별개로 추가한 클래스

# ── 세계 크기 ──────────────────────────────────────────────
WORLD_W = 360
WORLD_H = 240
SEA_LINE = WORLD_H * 0.45     # y < SEA_LINE = 빙판, 이상 = 바다

ATTACK_RANGE = 3.0            # 이 거리 안이면 사냥 시도 가능

# 종 클래스 모음
SPECIES_CLASSES = {
    "PolarBear": PolarBear, "ArcticFox": ArcticFox,
    "Penguin": Penguin, "Seal": Seal,
    "Orca": Orca, "ArcticCod": ArcticCod,
    "Krill": Krill, "Reindeer": Reindeer,
}

# 초기 개체수
INITIAL = {
    "Krill": 30, "ArcticCod": 50, "Reindeer": 18,
    "Penguin": 35, "Seal": 22, "Orca": 5,
    "PolarBear": 12, "ArcticFox": 12,
}

# "나를 먹는 포식자" 역참조 (도망 판단용)
def _build_threat_map():
    threat = {}
    for cls in SPECIES_CLASSES.values():
        for prey in getattr(cls, "PREY", ()):
            threat.setdefault(prey, set()).add(cls.SPECIES)
    # 크릴을 먹는 종도 위협으로 등록(크릴은 도망 안 하지만 일관성 위해)
    return threat

THREAT_MAP = _build_threat_map()


class Carcass:
    """동물이 죽으면 남는 사체. 여우/곰이 청소(scavenge)."""
    __slots__ = ("x", "y", "food", "ttl")
    def __init__(self, x, y, food, ttl=35):
        self.x, self.y, self.food, self.ttl = x, y, food, ttl


class Simulation:
    """전체 극지방 생태계 시뮬레이션."""

    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.world_w = WORLD_W
        self.world_h = WORLD_H
        self.sea_line = SEA_LINE        # 명목값(지형은 terrain 이 동적으로 관리)
        self.turn = 0
        self.running = True
        self.end_reason = None

        # ── 지구 온난화(AI 사용으로 인한) ─────────────────────
        # '온도를 올리는 기작'만 한다. 온도가 오르면 빙하가 녹고 수온이 올라
        # 서식지 상실·열 스트레스로 위 영양단계부터 자연 붕괴한다.
        # 멸망 = 크릴을 제외한 모든 생물이 사라진 시점.
        self.enable_warming = True
        self.warming = 0.0
        self.warming_rate = 0.0015      # 매 턴 온난화 증가량(가속)

        # 동적 지형/기후
        self.terrain = Terrain(self.world_w, self.world_h, seed=seed)

        self.animals = []
        self.carcasses = []
        self.log = []
        self.event_history = []
        self.last_collapse = None

        # 이끼(순록 먹이) 재생 자원
        self.lichen = 800.0
        self.LICHEN_CAP = 1200.0
        self.LICHEN_R = 0.12

        self._spawn_initial()
        self.history = {s: [] for s in SPECIES_CLASSES}
        self.history["KrillBiomass"] = []
        self.history["IceFraction"] = []
        self.history["Warming"] = []
        self.history["WaterTemp"] = []


        # ─────────────────────────────────────────────────────────
        # [추가] GUI 시각 효과 애니메이션을 위한 이벤트 저장소
        self.visual_effects = []  # [('hunt', x, y), ('reproduce', x, y)] 형태로 저장됨
        # ─────────────────────────────────────────────────────────
    
    # ── 초기 배치(지형 기반) ─────────────────────────────────
    def _rand_pos(self, habitat):
        if habitat == "ice":
            return self.terrain.random_ice_pos(random)
        elif habitat == "water":
            return self.terrain.random_water_pos(random)
        else:  # 반수생: 얼음/물 아무 곳
            if random.random() < 0.5:
                return self.terrain.random_ice_pos(random)
            return self.terrain.random_water_pos(random)

    def _spawn_initial(self):
        for species, n in INITIAL.items():
            cls = SPECIES_CLASSES[species]
            for _ in range(n):
                x, y = self._rand_pos(cls.HABITAT)
                self.animals.append(cls(x=x, y=y))

    def _spawn_krill(self):
        x, y = self.terrain.random_water_pos(random)
        k = Krill(x=x, y=y)
        self.animals.append(k)
        return k

    # ── 개체수 집계 ────────────────────────────────────────
    def counts(self):
        c = {s: 0 for s in SPECIES_CLASSES}
        for a in self.animals:
            if a.is_alive:
                c[a.SPECIES] += 1
        return c

    def krill_biomass(self):
        return sum(a.swarm_size for a in self.animals
                   if a.SPECIES == "Krill" and a.is_alive)

    # ── 공간 격자(근접 탐색 가속) ───────────────────────────
    _CELL = 32  # >= 최대 탐지 반경(범고래 30)

    def _build_grid(self):
        self._grid = {}
        for a in self.animals:
            if a.is_alive:
                key = (int(a.x // self._CELL), int(a.y // self._CELL))
                self._grid.setdefault(key, []).append(a)

    # ── 탐색 헬퍼(격자 3x3 이웃만 검사) ──────────────────────
    def _nearest(self, src, predicate, max_dist):
        best, best_d = None, max_dist
        cx, cy = int(src.x // self._CELL), int(src.y // self._CELL)
        grid = self._grid
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for a in grid.get((gx, gy), ()):
                    if a is src or not a.is_alive:
                        continue
                    if not predicate(a):
                        continue
                    d = src.get_distance(a)
                    if d < best_d:
                        best, best_d = a, d
        return best, best_d

    # ============================================================
    #                       메인 스텝
    # ============================================================
    def step(self):
        if not self.running:
            return
        self.turn += 1
        self.log = []

        # 0) 지구 온난화 진행 + 지형(빙하/수온) 갱신
        if self.enable_warming:
            # 가속 온난화: 시간이 갈수록 더 빨리 더워진다(AI 무한질주)
            self.warming += self.warming_rate * (1.0 + self.turn / 600.0)
        self.terrain.update(self.turn, self.warming)

        self._update_krill()
        self._update_lichen()
        self._update_carcasses()

        # 1) 갱신(나이/굶주림/아사) + 기후 피해(열 스트레스/빙하 상실)
        for a in self.animals:
            a.update()
        self._apply_climate()

        # 저밀도 은신처 계산용 개체수 캐시 + 공간 격자 구축
        self._counts = self.counts()
        self._build_grid()

        # 2) 행동(이동 + 섭식)
        actors = [a for a in self.animals if a.is_alive and a.SPECIES != "Krill"]
        random.shuffle(actors)
        for a in actors:
            self._behave(a)

        # 3) 번식(밀도의존)
        self._reproduce()

        # 4) 사망 정리 + 사체 생성
        self._cleanup()

        # 5) 이벤트
        self._events()

        # 6) 멸망 조건: 크릴을 제외한 모든 생물이 사라지면 종료
        c = self.counts()
        non_krill = sum(v for s, v in c.items() if s != "Krill")
        if non_krill == 0 and self.running:
            self.running = False
            self.end_reason = ("AI 지구 온난화로 빙하가 녹고 수온이 올라, "
                               "크릴을 제외한 모든 생물이 사라졌습니다.")

        # 7) 통계
        self._record_event_history()

        for s in SPECIES_CLASSES:
            self.history[s].append(c[s])
        self.history["KrillBiomass"].append(self.krill_biomass())
        self.history["IceFraction"].append(self.terrain.ice_fraction())
        self.history["Warming"].append(self.warming)
        self.history["WaterTemp"].append(self.terrain.water_temp)
        if len(self.visual_effects) > 100:
            self.visual_effects = self.visual_effects[-100:]
    # ── 기후 피해: 열 스트레스 + 빙하 상실 ───────────────────
    def _apply_climate(self):
        wt = self.terrain.water_temp
        for a in self.animals:
            if not a.is_alive or a.SPECIES == "Krill":
                continue
            if a.SPECIES == "Reindeer" and not self.terrain.is_ice_at(a.x, a.y):
                a.hp = 0
                continue
            # 열 스트레스: 해양/반수생은 수온, 육상(빙하)동물은 공기온도 기준
            if a.HABITAT == "ice":
                temp = self.terrain.air_temp_at(a.x, a.y)
            else:
                temp = wt
            over = temp - a.TEMP_TOLERANCE
            if over > 0:
                a.take_damage(over * a.THERMAL_K)
            # 빙하 상실: 빙하 동물이 유빙에서 떨어졌고, 가까운 유빙도 없어
            # '고립'되면 피해(온난화로 유빙이 사라지면 갈 곳이 없어진다)
            if a.ICE_LOSS_DMG > 0 and a.is_alive \
                    and not self.terrain.is_ice_at(a.x, a.y) \
                    and self.terrain.dist_to_ice(a.x, a.y) > self.terrain.STRAND_DIST:
                a.take_damage(a.ICE_LOSS_DMG)

    # ── 크릴 바이오매스(로지스틱 + 바닥 floor) ────────────────
    def _update_krill(self):
        krill = [a for a in self.animals if a.SPECIES == "Krill" and a.is_alive]
        total = sum(k.swarm_size for k in krill)

        # 바닥 floor: 먹이사슬 토대가 0 으로 사라지지 않게(소량 유입)
        if total < 80:
            nk = self._spawn_krill()
            krill.append(nk)
            total += nk.swarm_size

        cap = Krill.BIOMASS_CAP
        if total > 0 and total < cap:
            growth = Krill.GROWTH_R * total * (1.0 - total / cap)
            for k in krill:
                add = growth * (k.swarm_size / total)
                k.swarm_size = min(Krill.PER_OBJ_MAX, k.swarm_size + add)
            total = sum(k.swarm_size for k in krill)

        # 하드 클램프: 어떤 경우에도 전체 바이오매스가 상한을 넘지 않게
        if total > cap and total > 0:
            scale = cap / total
            for k in krill:
                k.swarm_size *= scale
            total = cap

        # 떼 객체가 적고 바이오매스가 충분하면 '기존 떼에서 분할'해 분산
        # (새 생물량을 주입하지 않으므로 폭증 불가)
        if (len(krill) < Krill.CARRYING_CAPACITY and krill
                and total > len(krill) * Krill.PER_OBJ_START * 0.85):
            biggest = max(krill, key=lambda k: k.swarm_size)
            if biggest.swarm_size > Krill.PER_OBJ_START:
                half = biggest.swarm_size / 2.0
                biggest.swarm_size = half
                nk = self._spawn_krill()
                nk.swarm_size = half

        for k in krill:
            k.drift(self.world_w, self.world_h, self.sea_line, terrain=self.terrain)
            # drift 후에도 빙하 위에 있으면 즉시 바다로 워프
            if self.terrain.is_ice_at(k.x, k.y):
                wx, wy = self.terrain.random_water_pos()
                k.x, k.y = wx, wy

    # ── 이끼 재생(로지스틱) ──────────────────────────────────
    def _update_lichen(self):
        L = self.lichen
        self.lichen = min(self.LICHEN_CAP,
                          L + self.LICHEN_R * L * (1 - L / self.LICHEN_CAP)*3/4)

    def _update_carcasses(self):
        for c in self.carcasses:
            c.ttl -= 1
        self.carcasses = [c for c in self.carcasses if c.ttl > 0 and c.food > 0]

    # ── 개체 행동 ──────────────────────────────────────────
    def _behave(self, a):
        sp = a.SPECIES

        # 서식지 유지: 빙하 동물이 녹은 바다 위면 가장 가까운 얼음으로 피신
        # (온난화로 얼음이 줄면 갈 곳이 없어 자연히 죽는다 = 멸망 기작의 일부)
        if a.HABITAT == "ice" and not self.terrain.is_ice_at(a.x, a.y):
            ice = self.terrain.nearest_ice(a.x, a.y)
            if ice is not None:
                a.state = "fleeing"
                a.move_toward(ice[0], ice[1], self.world_w, self.world_h)
                a._clamp(self.world_w, self.world_h)
                return
            # 얼음이 아예 없으면 갈 곳 없음 → 제자리 대기(곧 ICE_LOSS_DMG로 사망)
            a.state = "idle"
            return
        # 해양 동물이 얼음 위(표면 결빙)면 트인 물로 살짝 이동
        # 해양 동물(크릴·대구·Orca 등)이 빙하 위에 있으면 즉시 바다로 워프
        # move_toward로 밀면 빙하가 빠르게 덮을 때 탈출 못하는 경우가 생김
        elif a.HABITAT == "water" and self.terrain.is_ice_at(a.x, a.y):
            wx, wy = self.terrain.random_water_pos()
            a.x, a.y = wx, wy
            a._clamp(self.world_w, self.world_h)

        # 도망: 나를 먹는 포식자가 가까우면 회피(피식자 refuge → 안정화)
        threats = THREAT_MAP.get(sp)
        if threats:
            # 순록은 herd_alertness()로 탐지 반경 동적 적용
            detect_r = (a.herd_alertness() if sp == "Reindeer" else a.DETECTION)
            pred, d = self._nearest(
                a, lambda o: o.SPECIES in threats, detect_r)
            if pred is not None and d < detect_r * 0.6:
                a.state = "fleeing"
                prev_x, prev_y = a.x, a.y
                a.move_away(pred.x, pred.y, self.world_w, self.world_h)
                a._clamp(self.world_w, self.world_h)
                # 빙하 동물이 도망치다 바다로 나가는 것 방지
                if a.HABITAT == "ice" and not self.terrain.is_ice_at(a.x, a.y):
                    a.x, a.y = prev_x, prev_y
                if a.hunger <= a.WELLFED_HUNGER + 20:
                    return  # 위급하지 않으면 도망에 집중

        # 배가 충분히 차 있으면 사냥/섭식하지 않고 쉰다(포식압 자기억제).
        # 이 한 줄이 '포식량 ≤ 먹이 생산량' 을 만들어 사슬을 유지하는 핵심.
        hungry = a.hunger > getattr(a, "FEED_HUNGER", 35.0)
        if not hungry:
            a.state = "idle"
            a.random_walk(self.world_w, self.world_h)
            a._clamp(self.world_w, self.world_h)
            return

        # 순록: 이끼 먹기
        if sp == "Reindeer":
            self._graze(a)
            return

        # 여우: 사체 청소 + 소형 먹이
        if sp == "ArcticFox":
            self._fox_feed(a)
            return

        # 대구: school_move() — 계획서 상호작용
        # 포식자(Orca·Penguin·Seal) 탐지 시 같은 종 무리 쪽으로 뭉쳐서 도망.
        # 탐지만 해도 번식 쿨다운 증가(스트레스 번식 지연).
        if sp == "ArcticCod":
            self._cod_school_move(a)
            return

        # 포식자: 사냥
        prey_types = getattr(a, "PREY", ())
        ate = False
        if prey_types:
            ate = self._hunt(a, prey_types)
        if not ate and getattr(a, "EATS_KRILL", False):
            ate = self._eat_krill(a)
        if not ate:
            prev_x, prev_y = a.x, a.y
            a.random_walk(self.world_w, self.world_h)
            # 빙하 동물이 바다로 빠져나가는 것 방지
            if a.HABITAT == "ice" and not self.terrain.is_ice_at(a.x, a.y):
                a.x, a.y = prev_x, prev_y
            a._clamp(self.world_w, self.world_h)

    def _hunt(self, pred, prey_types):
        # 종별 동적 탐지 반경 계산
        if pred.SPECIES == "Orca":
            detect_range = pred.pod_signal_strength()
        elif pred.SPECIES == "PolarBear":
            detect_range = pred.ice_patrol_radius()
        else:
            detect_range = pred.DETECTION

        prey, d = self._nearest(
            pred, lambda o: o.SPECIES in prey_types, detect_range)
        if prey is None:
            return False
        if pred.SPECIES == "Orca":
            if pred.echo_ring <= 0:
                pred.echo_ring = 20
        if d > ATTACK_RANGE:
            pred.state = "hunting"
            pred.move_toward(prey.x, prey.y, self.world_w, self.world_h)
            pred._clamp(self.world_w, self.world_h)
            return False
        # 사냥 시도(포화형: 매우 굶주리면 성공률 약간 ↑)
        success = pred.HUNT_SUCCESS + (0.15 if pred.hunger > 80 else 0.0)
        
        # 저밀도 은신처(Holling type III): 피식종이 희소하면 잡기 매우 어려움
        # → 희소종이 0 으로 내몰리지 않고 강하게 회복(0 부근에 강한 복원력).
        prey_n = getattr(self, "_counts", {}).get(prey.SPECIES, 999)
        ratio = min(1.0, prey_n / 28.0)
        refuge = max(0.12, ratio ** 1.4)
        success *= refuge
        if random.random() < success:
            prey.take_damage(99999)
            pred.eat(pred.EAT_GAIN)

            
            # [추가] 사냥 성공한 타겟 동물의 위치를 이펙트 큐에 등록
            self.visual_effects.append(('hunt', pred.x, pred.y))
            # ─────────────────────────────────────────────────────────
            return True
        return False

    def _eat_krill(self, pred):
        krill, d = self._nearest(
            pred, lambda o: o.SPECIES == "Krill", pred.DETECTION)
        if krill is None:
            return False
        if d > ATTACK_RANGE:
            pred.move_toward(krill.x, krill.y, self.world_w, self.world_h)
            pred._clamp(self.world_w, self.world_h)
            return False
        take = getattr(pred, "KRILL_TAKE", 12.0)
        eaten = krill.grazed(take)
        if eaten <= 0:
            return False
        # 대구는 크릴이 주식(EAT_GAIN), 펭귄/물범은 보조(KRILL_GAIN)
        gain = getattr(pred, "KRILL_GAIN", getattr(pred, "EAT_GAIN", 30.0))
        pred.eat(gain * (eaten / max(take, 1e-6)))
        return True

    def _graze(self, deer):
        if deer.hunger > 20 and self.lichen > deer.GRAZE_COST:
            self.lichen -= deer.GRAZE_COST
            deer.eat(deer.GRAZE_GAIN)
            # 먹는 중엔 제자리 (가끔만 조금 움직임)
            prev_x ,prev_y = deer.x, deer.y
            if not self.terrain.is_ice_at(deer.x, deer.y):
                    deer.x, deer.y = prev_x, prev_y
                    deer._wander_dx *= -0.5  # ← 추가
                    deer._wander_dy *= -0.5  # ← 추가
                    prev_x, prev_y = deer.x, deer.y
            if random.random() < 0.3:
                
                deer.random_walk(self.world_w, self.world_h)
                # 이동 후 빙하 밖이면 원위치로 되돌림
                if not self.terrain.is_ice_at(deer.x, deer.y):
                    deer.x, deer.y = prev_x, prev_y
                    deer._wander_dx *= -0.5  # ← 추가
                    deer._wander_dy *= -0.5  # ← 추가
        else:
            prev_x, prev_y = deer.x, deer.y
            deer.random_walk(self.world_w, self.world_h)
            # 이동 후 빙하 밖이면 원위치로 되돌림
            if not self.terrain.is_ice_at(deer.x, deer.y):
                deer.x, deer.y = prev_x, prev_y
        deer._clamp(self.world_w, self.world_h)

    def _fox_feed(self, fox):
        # 1순위: 사체 청소
        best, bd = None, fox.DETECTION
        for c in self.carcasses:
            dd = math.hypot(fox.x - c.x, fox.y - c.y)
            if dd < bd:
                best, bd = c, dd
        if best is not None:
            if bd > ATTACK_RANGE:
                fox.move_toward(best.x, best.y, self.world_w, self.world_h)
                fox.state = "scavenging"
            else:
                take = min(best.food, fox.CARCASS_GAIN)
                best.food -= take
                fox.eat(take)
            fox._clamp(self.world_w, self.world_h)
            return

        # 2순위: 소형 먹이 채집 (배부를수록 효율 ↑ — foraging_efficiency 적용)
        if fox.hunger > 25 and random.random() < fox.foraging_efficiency():
            fox.eat(fox.FORAGE_GAIN)
            fox.random_walk(self.world_w, self.world_h)
            fox._clamp(self.world_w, self.world_h)
            return

        # 3순위: follow(PolarBear) — scavenging 하는거
        # 사체도 없고 채집도 실패하면, 가장 가까운 북극곰을 몰래 따라다닌다.
        # 곰이 사냥에 성공하면 그 자리에 사체가 생겨 1순위로 다음 턴에 먹게 된다.
        bear, bear_d = self._nearest(
            fox, lambda o: o.SPECIES == "PolarBear" and o.is_alive, fox.DETECTION * 1.5)
        if bear is not None:
            # 곰 바로 옆까지 붙지 않고 살짝 거리를 두며 따라감 (5칸 거리 유지)
            FOLLOW_DIST = 5.0
            if bear_d > FOLLOW_DIST + fox.speed:
                fox.state = "scavenging"  # 청소부 추적 중
                fox.move_toward(bear.x, bear.y, self.world_w, self.world_h)
            else:
                fox.random_walk(self.world_w, self.world_h)
            fox._clamp(self.world_w, self.world_h)
            return

        fox.random_walk(self.world_w, self.world_h)
        fox._clamp(self.world_w, self.world_h)

    # ── 대구 무리 이동 (school_move) ────────────────────────────
    def _cod_school_move(self, cod):
        """
        ArcticCod.school_move() — 계획서 상호작용 구현.

        1) 포식자(Orca·Penguin·Seal) 탐지 시:
           - 같은 종 무리의 무게중심 방향으로 이동(무리로 뭉치기).
           - 탐지만 해도 repro_cd += 3 (스트레스로 번식 지연).
        2) 포식자 없으면 크릴을 찾아 먹는 기존 행동.
        """
        COD_PREDATORS = ("Orca", "Penguin", "Seal")
        pred, pd = self._nearest(
            cod, lambda o: o.SPECIES in COD_PREDATORS, cod.DETECTION)

        if pred is not None:
            # 스트레스 번식 지연: 탐지만 해도 쿨다운 증가
            cod.repro_cd = min(cod.repro_cd + 3, cod.REPRO_COOLDOWN)
            cod.state = "fleeing"

            # schooling_bias: 배부를수록 더 넓게 무리를 탐색
            school_r = int(cod.schooling_bias() / self._CELL) + 1

            # 무리 무게중심 계산: schooling_bias 반경 안의 같은 종
            schoolmates = [
                o for o in self._grid.get(
                    (int(cod.x // self._CELL), int(cod.y // self._CELL)), [])
                if o is not cod and o.is_alive and o.SPECIES == "ArcticCod"
            ]
            # 인접 셀까지 확장 (school_r 반경)
            cx, cy = int(cod.x // self._CELL), int(cod.y // self._CELL)
            for gx in range(cx - school_r, cx + school_r + 1):
                for gy in range(cy - school_r, cy + school_r + 1):
                    if gx == cx and gy == cy:
                        continue
                    schoolmates += [
                        o for o in self._grid.get((gx, gy), [])
                        if o is not cod and o.is_alive and o.SPECIES == "ArcticCod"
                    ]

            if schoolmates:
                # 무리 중심으로 이동하면서 포식자 반대 방향으로 편향
                mx = sum(o.x for o in schoolmates) / len(schoolmates)
                my = sum(o.y for o in schoolmates) / len(schoolmates)
                # 무리 중심 방향 벡터
                tx = mx - cod.x + (cod.x - pred.x) * 0.6
                ty = my - cod.y + (cod.y - pred.y) * 0.6
            else:
                # 무리 없으면 포식자에서 직접 도망
                tx = cod.x - pred.x
                ty = cod.y - pred.y

            dist = math.hypot(tx, ty)
            if dist > 1e-9:
                cod.x += (tx / dist) * cod.speed
                cod.y += (ty / dist) * cod.speed
                cod.facing = 1 if tx >= 0 else -1
            cod._clamp(self.world_w, self.world_h)
            return

        # 포식자 없으면 크릴 섭식
        if not self._eat_krill(cod):
            cod.random_walk(self.world_w, self.world_h)
            cod._clamp(self.world_w, self.world_h)

    # ── 번식(밀도의존 로지스틱) ──────────────────────────────
    def _reproduce(self):
        c = self.counts()
        newborns = []

        # 유성생식: 같은 종 암수를 짝지어 번식
        # 종별로 번식 가능한 암/수 목록을 만들고 짝 매칭
        sexual_by_species = {}
        asexual = []
        for a in self.animals:
            if not a.is_alive or a.SPECIES == "Krill":
                continue
            if a.SEXUAL:
                sexual_by_species.setdefault(a.SPECIES, {"M": [], "F": []})
                key = "F" if a.gender == "F" else "M"
                sexual_by_species[a.SPECIES][key].append(a)
            else:
                asexual.append(a)

        # 유성생식: 암수 짝 매칭
        for sp, groups in sexual_by_species.items():
            n = c[sp]
            if n < 2:
                continue
            if not groups["M"] or not groups["F"]:
                continue  # 암수 중 한쪽이 없으면 건너뜀 (기존엔 조용히 실패)
            males = [m for m in groups["M"]
                     if m.can_reproduce(n) > 0 and m.can_reproduce_here(self.terrain)]
            females = [f for f in groups["F"]
                       if f.can_reproduce(n) > 0 and f.can_reproduce_here(self.terrain)]
            random.shuffle(males)
            random.shuffle(females)
            for male, female in zip(males, females):
                if c[sp] >= male.CARRYING_CAPACITY:
                    break
                # 두 개체의 번식 확률 평균으로 최종 확률 결정
                chance = (male.can_reproduce(n) + female.can_reproduce(n)) / 2
                if random.random() >= chance:
                    continue
                for _ in range(male.LITTER):
                    if c[sp] >= male.CARRYING_CAPACITY:
                        break
                    ox, oy = female.choose_offspring_position(self.terrain)
                    child = female.make_offspring(ox, oy)
                    child._clamp(self.world_w, self.world_h)
                    newborns.append(child)
                    c[sp] += 1
                # 번식 이펙트: 암컷 위치에 한 번만 등록 (LITTER 루프 밖)
                self.visual_effects.append(('reproduction', female.x, female.y))
                male.reset_repro()
                female.reset_repro()

        # 무성생식
        for a in asexual:
            n = c[a.SPECIES]
            if not a.can_reproduce_here(self.terrain):
                continue
            chance = a.can_reproduce(n)
            if chance <= 0:
                continue
            if random.random() < chance:
                for _ in range(a.LITTER):
                    if c[a.SPECIES] >= a.CARRYING_CAPACITY:
                        break
                    ox, oy = a.choose_offspring_position(self.terrain)
                    child = a.make_offspring(ox, oy)
                    child._clamp(self.world_w, self.world_h)
                    newborns.append(child)
                    c[a.SPECIES] += 1
                a.reset_repro()

        self.animals.extend(newborns)

    # ── 사망 정리 + 사체 ─────────────────────────────────────
    def _cleanup(self):
        survivors = []
        for a in self.animals:
            if a.is_alive:
                survivors.append(a)
            else:
                # 크릴 외에는 사체를 남김(에너지 순환)
                if a.SPECIES != "Krill":
                    food = 30.0 + a.max_hp * 0.25
                    self.carcasses.append(Carcass(a.x, a.y, food))
        self.animals = survivors
        self._build_grid()  # 시체 제거후 격자 즉시 갱신시키기
    # ── 이벤트 ─────────────────────────────────────────────
    def _events(self):
        # 눈보라: 40턴마다
        if self.turn % 40 == 0:
            self.log += Blizzard().trigger(self)
        # 빙하 붕괴: 매 턴 1.5% (얼음이 있는 구역 대상)
        if random.random() < 0.015 and self.terrain.ice_cells:
            self.log += GlacierCollapse().trigger(self)
        # 먹이 부족: 크릴 바이오매스가 바닥일 때만
        if self.krill_biomass() < 400:
            self.log += Starvation().trigger(self)
        # 계절 이동(rescue): 80턴마다, 위태로운 종에 소수 유입
        # (온난화가 심해지면 유입돼도 곧 죽으므로 멸망을 막지는 못한다)
        if self.turn % 80 == 0:
            self._seasonal_migration()
        # ※ 종료(멸망)는 더 이상 즉발 이벤트가 아니라, 온난화로 인한
        #    빙하 융해·수온 상승이 누적된 결과로 step() 에서 판정한다.

    def _seasonal_migration(self):
        """위태로운(1~3 마리) 종에 소수 개체 유입 — 우연한 전멸 방지.
        단, 그 종의 '서식 환경이 아직 살아있을 때만' 유입한다. 온난화로 빙하가
        녹거나(빙하 동물) 수온이 내성을 넘으면(해양 동물) 더는 유입하지 않아
        멸망이 온난화에 따라 자연스러운 순서로 진행된다."""
        c = self.counts()
        ice_ok = self.terrain.ice_fraction() > 0.2
        for sp, cls in SPECIES_CLASSES.items():
            if sp == "Krill" or not (0 < c[sp] <= 5):
                continue
            if cls.HABITAT == "ice":
                viable = ice_ok
            else:
                viable = self.terrain.water_temp < cls.TEMP_TOLERANCE - 1.0
            if not viable:
                continue
            for _ in range(2):
                x, y = self._rand_pos(cls.HABITAT)
                self.animals.append(cls(x=x, y=y))
            self.log.append(f"[계절 이동] {sp} 소수 개체가 합류했습니다.")

    # ── 헤드리스 실행(검증용) ────────────────────────────────
    def _record_event_history(self):
        for line in self.log:
            if line:
                self.event_history.append(f"[T{self.turn}] {line}")
        if len(self.event_history) > 200:
            self.event_history = self.event_history[-200:]

    def run_headless(self, turns, verbose_every=0):
        for _ in range(turns):
            if not self.running:
                break
            self.step()
            if verbose_every and self.turn % verbose_every == 0:
                c = self.counts()
                line = " ".join(f"{s[:4]}:{c[s]:>3}" for s in INITIAL)
                print(f"t{self.turn:>4} | {line} | krillBM:{self.krill_biomass():>6.0f}")
        return self


# ============================================================
#                  헤드리스 검증 함수
# ============================================================
def verify(seeds=(1, 7, 42, 123, 2024), turns=3000):
    print(f"=== 순수 생태 안정성 검증(지구 온난화 OFF): "
          f"{len(seeds)}개 시드 x {turns}턴 ===\n")
    import statistics
    all_ok = True
    for seed in seeds:
        sim = Simulation(seed=seed)
        sim.enable_warming = False             # 온난화 끄고 생태만 본다
        sim.run_headless(turns)
        c = sim.counts()
        extinct = [s for s in INITIAL if c[s] == 0]
        bm = sim.krill_biomass()
        mins = {s: min(sim.history[s]) for s in INITIAL}
        ice = sim.history["IceFraction"]
        ice_mean = statistics.mean(ice)
        ok = (len(extinct) == 0) and (bm <= Krill.BIOMASS_CAP + 1)
        all_ok = all_ok and ok
        status = "OK " if ok else "FAIL"
        print(f"[{status}] seed={seed:>4}  {turns}턴 완주  멸종:{extinct or '없음'}")
        cs = "  ".join(f"{s}:{c[s]}(min{mins[s]})" for s in INITIAL)
        print(f"        {cs}")
        print(f"        krillBiomass={bm:.0f}  빙하비율 평균={ice_mean:.2f} "
              f"(범위 {min(ice):.2f}~{max(ice):.2f})\n")
    print("=== 결과:",
          "모든 시드에서 8종 유지 + 빙하 비율 일정 — OK"
          if all_ok else "일부 시드 멸종 — 튜닝 필요", "===")
    return all_ok


def verify_warming(seed=42, turns=2500):
    """온난화 ON: 빙하/수온/개체수가 어떻게 붕괴해 '멸망'에 이르는지."""
    print(f"=== 지구 온난화 ON — 붕괴 시나리오 (seed={seed}) ===\n")
    sim = Simulation(seed=seed)
    sim.run_headless(turns, verbose_every=max(1, turns // 25))
    print(f"\n종료: turn {sim.turn}")
    print(f"사유: {sim.end_reason or '(미종료)'}")
    print(f"최종 개체수: {sim.counts()}")
    return sim


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--headless":
        t = int(sys.argv[2]) if len(sys.argv) >= 3 else 2000
        Simulation(seed=42).run_headless(t, verbose_every=max(1, t // 20))
    elif len(sys.argv) >= 2 and sys.argv[1] == "--verify":
        verify()
    elif len(sys.argv) >= 2 and sys.argv[1] == "--warming":
        t = int(sys.argv[2]) if len(sys.argv) >= 3 else 2500
        verify_warming(turns=t)
    else:
        try:
            import pygame  # noqa
            from viz import run_with_pygame
            run_with_pygame(Simulation())
        except ImportError:
            print("pygame 가 없어 헤드리스로 실행합니다. (pip install pygame)")
            Simulation(seed=42).run_headless(2000, verbose_every=100)
