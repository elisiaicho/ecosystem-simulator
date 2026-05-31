"""
terrain.py
----------
지형/기후 시스템 (담당: 공통 — System 에 통합)

[핵심 아이디어] 빙하를 '고정된 절반'이 아니라 **바다 위를 떠다니는 유빙(ice
floe) 덩어리**들로 만든다. 현실의 북극 유빙(pack ice)을 작게 축소한 모델이다.

- 유빙은 바다 곳곳에 **랜덤한 위치**에 **덩어리(섬)** 로 생성된다(너무 작지 않게,
  울퉁불퉁한 모양). 천천히 **떠다니며(drift)**, 시간이 지나면 녹아 사라지고
  다른 곳에 새 유빙이 생긴다.
- 온난화가 없으면: 생성(birth)과 융해(melt)가 균형을 이뤄 빙하 '비율'이 한
  목표값 근처에서 **랜덤하게(주기적 진동이 아니라)** 유지된다.
- 온난화가 오르면: 유빙이 더 빨리 녹고(melt↑) 새로 잘 생기지 않아(birth↓)
  빙하가 점점 사라진다 → 빙하 동물은 발 디딜 곳을 잃는다.
- 수온도 온난화에 비례해 오른다 → 냉수성 해양 동물이 열 스트레스로 죽는다.
"""

import math
import random


class _Floe:
    """떠다니는 유빙 한 덩어리. 본체 원 + 위성 원들로 울퉁불퉁한 섬 모양."""
    __slots__ = ("cx", "cy", "r", "vx", "vy", "bumps")

    def __init__(self, cx, cy, r, rng):
        self.cx, self.cy, self.r = cx, cy, r
        sp = rng.uniform(0.02, 0.06)          # 표류 속도(느리게)
        ang = rng.uniform(0, 2 * math.pi)
        self.vx, self.vy = sp * math.cos(ang), sp * math.sin(ang)
        # 위성 원(2~4개)로 비대칭/울퉁불퉁한 윤곽
        self.bumps = []
        for _ in range(rng.randint(2, 4)):
            a = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0.45, 0.85)    # 본체 반지름 대비
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
    TARGET_COV = 0.42        # 온난화 0일 때 유지할 목표 빙하 비율
    R_NEW_MIN, R_NEW_MAX = 6.0, 11.0   # 새 유빙 반지름(섬 크기)
    MIN_R = 3.5              # 이보다 작아지면 완전히 녹음
    BASE_SHRINK = 0.015      # 매 턴 기본 융해(반지름)
    WARM_SHRINK = 0.06       # 온난화 1도당 추가 융해
    FORM_CUTOFF = 6.0        # 온난화가 이 값 이상이면 새 유빙이 거의 안 생김
    MAX_BIRTH_PER_TURN = 2
    STRAND_DIST = 26.0       # 가장 가까운 유빙이 이보다 멀면 '고립'(빙하동물 피해)

    # 수온/공기온도
    WATER_BASE = -0.6
    AIR_BASE = -6.0
    AIR_NOISE = 2.0

    def __init__(self, world_w, world_h, seed=None, grid_w=60, grid_h=40):
        self.world_w = world_w
        self.world_h = world_h
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell_w = world_w / grid_w
        self.cell_h = world_h / grid_h
        self._rng = random.Random(seed)

        # 공기온도용 정적 노이즈(약간의 얼룩)
        self.noise = [[self._rng.uniform(-1, 1) * self.AIR_NOISE
                       for _ in range(grid_h)] for _ in range(grid_w)]
        self.air_off = 0.0      # 공기온도 = AIR_BASE + warming + noise

        self.floes = []
        self.ice = [[False] * grid_h for _ in range(grid_w)]
        self.ice_cells = []
        self.water_temp = self.WATER_BASE

        # 초기 유빙을 목표 비율까지 흩뿌림
        self._seed_initial()
        self._rasterize()

    # ── 유빙 생성/위치 ─────────────────────────────────────
    def _spawn_floe(self):
        r = self._rng.uniform(self.R_NEW_MIN, self.R_NEW_MAX)
        cx = self._rng.uniform(r, self.world_w - r)
        cy = self._rng.uniform(r, self.world_h - r)
        self.floes.append(_Floe(cx, cy, r, self._rng))

    def _seed_initial(self):
        guard = 0
        while self.ice_fraction_est() < self.TARGET_COV and guard < 60:
            self._spawn_floe()
            self._rasterize()
            guard += 1

    def ice_fraction_est(self):
        # 빠른 추정(원 면적 합 / 세계 면적). 겹침은 무시하므로 birth 제어용 근사.
        self._rasterize()
        return self.ice_fraction()

    # ── 매 턴 갱신 ─────────────────────────────────────────
    def update(self, turn, warming, init=False):
        self.water_temp = self.WATER_BASE + warming
        self.air_off = self.AIR_BASE + warming

        shrink = self.BASE_SHRINK + max(0.0, warming) * self.WARM_SHRINK
        # 1) 표류 + 융해 + 소멸
        for f in self.floes:
            f.cx += f.vx
            f.cy += f.vy
            # 가장자리에서 튕김(바다 안에서 떠다님)
            if f.cx < f.r or f.cx > self.world_w - f.r:
                f.vx = -f.vx
                f.cx = min(max(f.cx, f.r), self.world_w - f.r)
            if f.cy < f.r or f.cy > self.world_h - f.r:
                f.vy = -f.vy
                f.cy = min(max(f.cy, f.r), self.world_h - f.r)
            f.r -= shrink
            if self._rng.random() < 0.03:        # 가끔 균열(calving)로 더 줄어듦
                f.r -= self._rng.uniform(0.5, 1.5)
        self.floes = [f for f in self.floes if f.r >= self.MIN_R]

        # 2) 생성(birth): 목표 비율보다 적으면 새 유빙을 랜덤하게 추가.
        #    온난화가 심하면(추위가 부족하면) 거의 생기지 않는다.
        self._rasterize()
        cold = max(0.0, 1.0 - warming / self.FORM_CUTOFF)
        target = self.TARGET_COV * cold
        births = 0
        while (self.ice_fraction() < target
               and births < self.MAX_BIRTH_PER_TURN
               and self._rng.random() < 0.7):     # 확률 요소 → 랜덤한 변동
            self._spawn_floe()
            self._rasterize()
            births += 1

    # ── 격자 변환(조회·렌더용) ──────────────────────────────
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
        """가장 가까운 유빙의 중심(피신 목표). 없으면 None."""
        best, bd = None, 1e18
        for f in self.floes:
            d = math.hypot(x - f.cx, y - f.cy) - f.r
            if d < bd:
                bd, best = d, (f.cx, f.cy)
        return best

    def dist_to_ice(self, x, y):
        """가장 가까운 유빙 가장자리까지 거리(유빙 위면 0, 없으면 큰 값)."""
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
        for _ in range(40):
            x = rng.uniform(0, self.world_w - 1)
            y = rng.uniform(0, self.world_h - 1)
            if not self.is_ice_at(x, y):
                return x, y
        return rng.uniform(0, self.world_w), rng.uniform(0, self.world_h)
