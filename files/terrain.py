"""
terrain.py
----------
지형/기후 시스템 (담당: 공통 — System 에 통합)

[핵심 아이디어]
빙하를 '고정된 절반'이 아니라 '온도에 따라 얼고 녹는 동적 격자'로 만든다.

- 격자의 각 칸은 공기 온도(air)에 따라 결빙/융해한다.
    · air_temp < T_FREEZE  → 얼음 생성
    · air_temp > T_MELT    → 얼음 융해   (T_FREEZE < T_MELT, 이력현상으로 안정)
- 공기 온도 = 위도 그라데이션(위=극지방=추움) + 계절 + 칸별 노이즈 + 온난화
    → 온난화가 0이면 빙하 비율이 ~50% 에서 계절에 따라 출렁이며 유지(북극과 유사).
    → 온난화가 커지면 결빙선이 후퇴해 빙하가 사라진다.
- 수온(water)은 거의 균일한 차가운 바다 + 약한 계절 + 온난화.
    → 온난화 전에는 차가워 냉수성 종이 안전하고, 온난화가 진행되면 수온이
      종의 내성을 넘어 열 스트레스로 죽기 시작한다.

공기온도(빙하/육상동물)와 수온(해양동물)을 분리한 이유: 북극 바다는 어디서나
차갑지만, 빙하가 얼고 녹는 것은 표면 공기 온도가 결정하기 때문이다. 이렇게 해야
온난화가 없을 때 '빙하 ~50% 유지 + 해양종 안전'이 동시에 성립한다.
"""

import math
import random


class Terrain:
    ICE = "ice"
    WATER = "water"

    # 온도 상수(섭씨 느낌의 임의 단위)
    AIR_TOP = -11.0          # 맨 위(극) 공기 온도
    AIR_BOTTOM = 9.0         # 맨 아래 공기 온도
    T_FREEZE = -1.8          # 이 온도 미만이면 결빙
    T_MELT = 0.2             # 이 온도 초과면 융해(이력현상 band)
    SEASON_PERIOD = 360      # '1년' 턴 수
    SEASON_AMP_AIR = 6.0     # 공기 계절 진폭
    NOISE_AMP = 3.0          # 칸별 정적 노이즈 진폭

    WATER_BASE = -0.6        # 평상시 바다 온도(차가움)
    SEASON_AMP_WATER = 1.4

    def __init__(self, world_w, world_h, seed=None, grid_w=60, grid_h=40):
        self.world_w = world_w
        self.world_h = world_h
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell_w = world_w / grid_w
        self.cell_h = world_h / grid_h

        rng = random.Random(seed)
        # 위도 그라데이션(행별 기본 공기온도): 위=추움
        self.row_base = [
            self.AIR_TOP + (gy / (grid_h - 1)) * (self.AIR_BOTTOM - self.AIR_TOP)
            for gy in range(grid_h)
        ]
        # 칸별 정적 노이즈(약간 매끄럽게)
        raw = [[rng.uniform(-1, 1) for _ in range(grid_h)] for _ in range(grid_w)]
        self.noise = [[0.0] * grid_h for _ in range(grid_w)]
        for gx in range(grid_w):
            for gy in range(grid_h):
                acc, cnt = 0.0, 0
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = gx + dx, gy + dy
                        if 0 <= nx < grid_w and 0 <= ny < grid_h:
                            acc += raw[nx][ny]; cnt += 1
                self.noise[gx][gy] = (acc / cnt) * self.NOISE_AMP

        # 현재 상태 그리드
        self.air = [[0.0] * grid_h for _ in range(grid_w)]
        self.ice = [[False] * grid_h for _ in range(grid_w)]
        self.water_temp = self.WATER_BASE
        self.ice_cells = []      # 얼음 칸 중심 좌표 목록(최근접 탐색용)

        # 초기 상태: 온난화 0, 계절 0 으로 한 번 계산
        self.update(turn=0, warming=0.0, init=True)

    # ── 좌표 → 격자 인덱스 ──────────────────────────────────
    def _cell(self, x, y):
        gx = min(self.grid_w - 1, max(0, int(x / self.cell_w)))
        gy = min(self.grid_h - 1, max(0, int(y / self.cell_h)))
        return gx, gy

    # ── 매 턴 갱신 ─────────────────────────────────────────
    def update(self, turn, warming, init=False):
        season_air = self.SEASON_AMP_AIR * math.sin(
            2 * math.pi * turn / self.SEASON_PERIOD)
        season_water = self.SEASON_AMP_WATER * math.sin(
            2 * math.pi * turn / self.SEASON_PERIOD)

        self.water_temp = self.WATER_BASE + season_water + warming

        self.ice_cells = []
        for gx in range(self.grid_w):
            for gy in range(self.grid_h):
                t = self.row_base[gy] + season_air + self.noise[gx][gy] + warming
                self.air[gx][gy] = t
                if init:
                    self.ice[gx][gy] = (t < self.T_FREEZE)
                else:
                    # 이력현상: 얼면 T_MELT 넘어야 녹고, 녹으면 T_FREEZE 밑이라야 언다
                    if self.ice[gx][gy]:
                        if t > self.T_MELT:
                            self.ice[gx][gy] = False
                    else:
                        if t < self.T_FREEZE:
                            self.ice[gx][gy] = True
                if self.ice[gx][gy]:
                    self.ice_cells.append(
                        ((gx + 0.5) * self.cell_w, (gy + 0.5) * self.cell_h))

    # ── 조회 ───────────────────────────────────────────────
    def is_ice_at(self, x, y):
        gx, gy = self._cell(x, y)
        return self.ice[gx][gy]

    def air_temp_at(self, x, y):
        gx, gy = self._cell(x, y)
        return self.air[gx][gy]

    def ice_fraction(self):
        n = self.grid_w * self.grid_h
        return len(self.ice_cells) / n if n else 0.0

    def nearest_ice(self, x, y):
        """가장 가까운 얼음 칸 중심 좌표. 없으면 None."""
        best, bd = None, 1e18
        for cx, cy in self.ice_cells:
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d < bd:
                best, bd = (cx, cy), d
        return best

    def random_ice_pos(self, rng=random):
        if self.ice_cells:
            cx, cy = rng.choice(self.ice_cells)
            return (cx + rng.uniform(-self.cell_w / 2, self.cell_w / 2),
                    cy + rng.uniform(-self.cell_h / 2, self.cell_h / 2))
        return rng.uniform(0, self.world_w), rng.uniform(0, self.world_h * 0.3)

    def random_water_pos(self, rng=random):
        for _ in range(30):
            x = rng.uniform(0, self.world_w - 1)
            y = rng.uniform(0, self.world_h - 1)
            if not self.is_ice_at(x, y):
                return x, y
        return rng.uniform(0, self.world_w), rng.uniform(self.world_h * 0.7,
                                                         self.world_h - 1)
