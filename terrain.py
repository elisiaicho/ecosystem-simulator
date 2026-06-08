"""
terrain.py
----------
지형/기후 시스템 (담당: 공통 — System 에 통합)

[핵심 아이디어] 빙하를 '고정된 절반'이 아니라 **바다 위를 떠다니는 유빙(ice
floe) 덩어리**들로 만든다. 현실의 북극 유빙(pack ice)을 작게 축소한 모델이다.

- 유빙은 기존 유빙 가장자리에서 분리(calving)되어 흘러나온다.
  완전 랜덤 위치 생성 대신, 부모 유빙의 속도 방향을 이어받아 자연스럽게 이동한다.
- 유빙끼리 같은 방향으로 흐르는 '해류(current)' 효과를 추가했다.
  매 턴 전역 해류 벡터가 조금씩 바뀌며, 모든 유빙이 그 방향으로 편향된다.
- 온난화가 오르면: 유빙이 더 빨리 녹고 새로 잘 생기지 않아 빙하가 점점 사라진다.
- 수온도 온난화에 비례해 오른다.
"""

import math
import random


class _Floe:
    """떠다니는 유빙 한 덩어리. 본체 원 + 위성 원들로 울퉁불퉁한 섬 모양."""
    __slots__ = ("cx", "cy", "r", "vx", "vy", "bumps")

    def __init__(self, cx, cy, r, vx, vy, rng):
        self.cx, self.cy, self.r = cx, cy, r
        self.vx, self.vy = vx, vy
        # 위성 원(2~4개)로 비대칭/울퉁불퉁한 윤곽
        self.bumps = []
        for _ in range(rng.randint(2, 4)):
            a = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0.45, 0.85)
            br = rng.uniform(0.45, 0.7)
            self.bumps.append((dist * math.cos(a), dist * math.sin(a), br))

    def circles(self):
        """(중심x, 중심y, 반지름) 목록 — 본체 + 위성."""
        yield (self.cx, self.cy, self.r)
        for dx, dy, br in self.bumps:
            yield (self.cx + dx * self.r, self.cy + dy * self.r, br * self.r)


class Terrain:
    ICE = "ice"
    WATER = "water"

    # 빙하(유빙) 파라미터
    TARGET_COV = 0.42
    R_NEW_MIN, R_NEW_MAX = 12.0, 20.0
    MIN_R = 4.0              # 6.0 → 4.0: 더 작아질 때까지 버팀
    BASE_SHRINK = 0.005      # 0.015 → 0.005: 기본 융해 1/3로 감소
    WARM_SHRINK = 0.02       # 0.06 → 0.02: 온난화 피해도 1/3로 감소
    FORM_CUTOFF = 6.0
    MAX_BIRTH_PER_TURN = 1
    STRAND_DIST = 26.0

    # 해류 파라미터
    CURRENT_SPEED = 0.012    # 해류가 유빙에 가하는 힘(매 턴 vx/vy에 더해지는 양)
    CURRENT_TURN_RATE = 0.008 # 해류 방향이 매 턴 바뀌는 최대 각도(rad)
    FLOE_DRIFT_BASE = 0.008  # 유빙 자체 표류 속도(해류와 별개의 고유 속도)

    # 수온/공기온도
    WATER_BASE = -0.6
    AIR_BASE = -6.0
    AIR_NOISE = 2.0

    def __init__(self, world_w, world_h, seed=None, grid_w=120, grid_h=80):
        self.world_w = world_w
        self.world_h = world_h
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell_w = world_w / grid_w
        self.cell_h = world_h / grid_h
        self._rng = random.Random(seed)

        # 공기온도용 정적 노이즈
        self.noise = [[self._rng.uniform(-1, 1) * self.AIR_NOISE
                       for _ in range(grid_h)] for _ in range(grid_w)]
        self.air_off = 0.0

        # 전역 해류 벡터 — 모든 유빙이 이 방향으로 편향되어 흐름
        cur_ang = self._rng.uniform(0, 2 * math.pi)
        self.current_vx = math.cos(cur_ang) * self.CURRENT_SPEED
        self.current_vy = math.sin(cur_ang) * self.CURRENT_SPEED

        self.floes = []
        self.ice = [[False] * grid_h for _ in range(grid_w)]
        self.ice_cells = []
        self.water_temp = self.WATER_BASE

        self._seed_initial()
        self._rasterize()

    # ── 해류 갱신 ──────────────────────────────────────────
    def _update_current(self):
        """
        매 턴 해류 방향을 조금씩 틀어준다.
        급격히 바뀌지 않아서 유빙들이 한동안 같은 방향으로 흐르다가
        서서히 방향을 바꾸는 자연스러운 흐름이 만들어진다.
        """
        dang = self._rng.uniform(-self.CURRENT_TURN_RATE, self.CURRENT_TURN_RATE)
        cos_d, sin_d = math.cos(dang), math.sin(dang)
        new_vx = self.current_vx * cos_d - self.current_vy * sin_d
        new_vy = self.current_vx * sin_d + self.current_vy * cos_d
        # 속도 크기 고정
        mag = math.hypot(new_vx, new_vy)
        if mag > 1e-9:
            self.current_vx = new_vx / mag * self.CURRENT_SPEED
            self.current_vy = new_vy / mag * self.CURRENT_SPEED

    # ── 유빙 생성 ──────────────────────────────────────────
    def _make_floe(self, cx, cy, r, parent_vx=0.0, parent_vy=0.0):
        """
        유빙을 생성한다.
        부모 유빙이 있으면 그 속도 방향을 이어받고 약간 틀어서 분리된 느낌을 준다.
        해류 벡터도 합산해 전체 흐름 방향으로 편향된다.
        """
        # 고유 표류: 부모 방향 ± 약간의 각도 틀기
        base_ang = math.atan2(parent_vy, parent_vx) if (parent_vx or parent_vy) \
                   else self._rng.uniform(0, 2 * math.pi)
        drift_ang = base_ang + self._rng.uniform(-0.4, 0.4)
        sp = self.FLOE_DRIFT_BASE
        vx = math.cos(drift_ang) * sp + self.current_vx
        vy = math.sin(drift_ang) * sp + self.current_vy
        return _Floe(cx, cy, r, vx, vy, self._rng)

    def _spawn_floe_from_parent(self, parent):
        """
        부모 유빙 가장자리에서 작은 조각이 분리(calving)되어 흘러나온다.
        위치: 부모 가장자리 + 약간 바깥
        크기: 부모보다 작은 새 섬
        """
        r = self._rng.uniform(self.R_NEW_MIN, min(self.R_NEW_MAX, parent.r * 0.9))
        ang = self._rng.uniform(0, 2 * math.pi)
        # 부모 가장자리 바로 바깥에 붙여서 생성
        offset = parent.r + r * 0.8
        cx = parent.cx + math.cos(ang) * offset
        cy = parent.cy + math.sin(ang) * offset
        # 세계 밖으로 나가면 반대쪽으로
        cx = min(max(cx, r), self.world_w - r)
        cy = min(max(cy, r), self.world_h - r)
        self.floes.append(self._make_floe(cx, cy, r, parent.vx, parent.vy))

    def _spawn_floe_random(self):
        """초기 씨드용 — 부모 없이 랜덤 위치에 생성."""
        r = self._rng.uniform(self.R_NEW_MIN, self.R_NEW_MAX)
        cx = self._rng.uniform(r, self.world_w - r)
        cy = self._rng.uniform(r, self.world_h - r)
        self.floes.append(self._make_floe(cx, cy, r))

    def _seed_initial(self):
        guard = 0
        while self.ice_fraction_est() < self.TARGET_COV and guard < 60:
            self._spawn_floe_random()
            self._rasterize()
            guard += 1

    def ice_fraction_est(self):
        self._rasterize()
        return self.ice_fraction()

    # ── 매 턴 갱신 ─────────────────────────────────────────
    def update(self, turn, warming, init=False):
        self.water_temp = self.WATER_BASE + warming
        self.air_off = self.AIR_BASE + warming

        # 해류 방향 서서히 변경
        self._update_current()

        shrink = self.BASE_SHRINK + max(0.0, warming) * self.WARM_SHRINK

        # 1) 표류 + 해류 반영 + 융해 + 소멸
        for f in self.floes:
            # 해류 방향으로 속도를 조금씩 끌어당김 (관성 유지하면서 해류 따라감)
            f.vx += (self.current_vx - f.vx) * 0.05
            f.vy += (self.current_vy - f.vy) * 0.05

            f.cx += f.vx
            f.cy += f.vy

            # 벽 튕김
            if f.cx < f.r or f.cx > self.world_w - f.r:
                f.vx = -f.vx
                f.cx = min(max(f.cx, f.r), self.world_w - f.r)
            if f.cy < f.r or f.cy > self.world_h - f.r:
                f.vy = -f.vy
                f.cy = min(max(f.cy, f.r), self.world_h - f.r)

            # 융해
            f.r -= shrink
            # 가끔 균열로 추가 감소
            if self._rng.random() < 0.01:        # 0.03 → 0.01: 균열 확률 1/3로 감소
                f.r -= self._rng.uniform(0.1, 0.4)  # 0.5~1.5 → 0.1~0.4: 균열 크기도 감소

        self.floes = [f for f in self.floes if f.r >= self.MIN_R]

        # 2) 생성(calving): 기존 유빙에서 분리되어 새 조각이 흘러나옴
        self._rasterize()
        cold = max(0.0, 1.0 - warming / self.FORM_CUTOFF)
        target = self.TARGET_COV * cold
        births = 0
        while (self.ice_fraction() < target
               and births < self.MAX_BIRTH_PER_TURN
               and self._rng.random() < 0.7):
            if self.floes:
                # 가장 큰 유빙에서 분리 — 자연스러운 calving
                parent = max(self.floes, key=lambda f: f.r)
                self._spawn_floe_from_parent(parent)
            else:
                # 유빙이 전혀 없을 때만 랜덤 생성
                self._spawn_floe_random()
            self._rasterize()
            births += 1

    # ── 격자 변환 ───────────────────────────────────────────
    def _rasterize(self):
        for gx in range(self.grid_w):
            row = self.ice[gx]
            for gy in range(self.grid_h):
                row[gy] = False
        for f in self.floes:
            for (ccx, ccy, cr) in f.circles():
                gx0 = max(0, int((ccx - cr) / self.cell_w))
                gx1 = min(self.grid_w - 1, int((ccx + cr) / self.cell_w))
                gy0 = max(0, int((ccy - cr) / self.cell_h))
                gy1 = min(self.grid_h - 1, int((ccy + cr) / self.cell_h))
                cr2 = cr * cr
                for gx in range(gx0, gx1 + 1):
                    cellx = (gx + 0.5) * self.cell_w
                    for gy in range(gy0, gy1 + 1):
                        celly = (gy + 0.5) * self.cell_h
                        if (cellx - ccx) ** 2 + (celly - ccy) ** 2 <= cr2:
                            self.ice[gx][gy] = True
        self.ice_cells = [((gx + 0.5) * self.cell_w, (gy + 0.5) * self.cell_h)
                          for gx in range(self.grid_w)
                          for gy in range(self.grid_h) if self.ice[gx][gy]]

    # ── 조회 ───────────────────────────────────────────────
    def _cell(self, x, y):
        gx = min(self.grid_w - 1, max(0, int(x / self.cell_w)))
        gy = min(self.grid_h - 1, max(0, int(y / self.cell_h)))
        return gx, gy

    def is_ice_at(self, x, y):
        gx, gy = self._cell(x, y)
        return self.ice[gx][gy]

    def air_temp_at(self, x, y):
        gx, gy = self._cell(x, y)
        return self.air_off + self.noise[gx][gy]

    def ice_fraction(self):
        n = self.grid_w * self.grid_h
        return len(self.ice_cells) / n if n else 0.0

    def nearest_ice(self, x, y):
        best, bd = None, 1e18
        for f in self.floes:
            d = math.hypot(x - f.cx, y - f.cy) - f.r
            if d < bd:
                bd, best = d, (f.cx, f.cy)
        return best

    def dist_to_ice(self, x, y):
        if not self.floes:
            return 1e18
        return max(0.0, min(math.hypot(x - f.cx, y - f.cy) - f.r
                            for f in self.floes))

    def random_ice_pos(self, rng=random):
        if self.floes:
            f = rng.choice(self.floes)
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0, f.r * 0.7)
            return f.cx + d * math.cos(a), f.cy + d * math.sin(a)
        return rng.uniform(0, self.world_w), rng.uniform(0, self.world_h)

    def random_water_pos(self, rng=random):
        for _ in range(4000):
            x = rng.uniform(0, self.world_w - 1)
            y = rng.uniform(0, self.world_h - 1)
            if not self.is_ice_at(x, y):
                return x, y
        return rng.uniform(0, self.world_w), rng.uniform(0, self.world_h)
