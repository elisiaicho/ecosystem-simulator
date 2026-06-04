"""
viz.py
------
pygame 실시간 시각화

main.py 의 Simulation 을 받아 매 프레임 step() 을 호출하고 그려준다.
외부 이미지 없이 도형으로 종별 스프라이트를 그린다.

조작:
  ESC    종료
  Space  일시정지/재개
  F      빠르게(한 프레임에 여러 step)
  M      AI 폭주(종료 이벤트) 강제 발동
"""

import pygame

# 화면 배치
SCALE = 8                                  # 시뮬 1칸 = 8픽셀
UI_W = 300

C_ICE   = (224, 236, 246)
C_ICE2  = (205, 222, 238)
C_SEA   = (28, 74, 122)
C_SEA2  = (20, 58, 100)
C_PANEL = (24, 28, 38)
C_TEXT  = (232, 236, 242)
C_TITLE = (150, 205, 255)
C_RED   = (224, 96, 96)
C_GREEN = (120, 210, 140)

SPECIES_COLOR = {
    "PolarBear": (248, 248, 250),
    "ArcticFox": (226, 206, 170),
    "Penguin":   (32, 34, 44),
    "Seal":      (120, 120, 132),
    "Orca":      (16, 18, 30),
    "ArcticCod": (176, 188, 206),
    "Krill":     (250, 132, 92),
    "Reindeer":  (122, 86, 56),
}
SPECIES_R = {  # 그리기 반지름(픽셀)
    "PolarBear": 7, "ArcticFox": 4, "Penguin": 4, "Seal": 5,
    "Orca": 9, "ArcticCod": 3, "Krill": 2, "Reindeer": 6,
}
ORDER = ["Krill", "ArcticCod", "Reindeer", "Penguin",
         "Seal", "Orca", "PolarBear", "ArcticFox"]
KOR = {
    "PolarBear": "북극곰", "ArcticFox": "북극여우", "Penguin": "펭귄",
    "Seal": "바다표범", "Orca": "범고래", "ArcticCod": "북극대구",
    "Krill": "크릴", "Reindeer": "순록",
}


def run_with_pygame(sim):
    pygame.init()
    sw = sim.world_w * SCALE
    sh = sim.world_h * SCALE
    screen = pygame.display.set_mode((sw + UI_W, sh))
    pygame.display.set_caption("극지방의 아이들 — 생태계 시뮬레이션")
    clock = pygame.time.Clock()

    def font(sz, bold=False):
        try:
            return pygame.font.SysFont("malgungothic,applegothic,notosanscjk",
                                       sz, bold=bold)
        except Exception:
            return pygame.font.Font(None, sz)
    f_sm, f_md, f_bg = font(15), font(18, True), font(26, True)

    sea_y = int(sim.sea_line * SCALE)
    fast = False
    paused = False
    running = True

    def sx(x): return int(x * SCALE)
    def sy(y): return int(y * SCALE)

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_f:
                    fast = not fast
                elif e.key == pygame.K_m:
                    sim.warming += 3.0   # 온난화 가속(시연용): 즉시 +3도

        # 시뮬 진행
        if not paused and sim.running:
            steps = 4 if fast else 1
            for _ in range(steps):
                if sim.running:
                    sim.step()

        # ── 배경: 동적 빙하 격자 (온도로 얼고 녹음) ──
        terr = sim.terrain
        cw = terr.cell_w * SCALE
        ch = terr.cell_h * SCALE
        # 수온이 오를수록 바다를 붉게(따뜻하게)
        wt = terr.water_temp
        warm_f = max(0.0, min(1.0, (wt + 1.0) / 10.0))
        sea_col = (int(C_SEA[0] + warm_f * 90),
                   int(C_SEA[1] + warm_f * 20),
                   int(C_SEA[2] - warm_f * 60))
        for gx in range(terr.grid_w):
            for gy in range(terr.grid_h):
                rx, ry = int(gx * cw), int(gy * ch)
                if terr.ice[gx][gy]:
                    pygame.draw.rect(screen, C_ICE,
                                     (rx, ry, int(cw) + 1, int(ch) + 1))
                else:
                    pygame.draw.rect(screen, sea_col,
                                     (rx, ry, int(cw) + 1, int(ch) + 1))

        # 빙하 붕괴 표시(잠깐)
        if sim.last_collapse:
            cx, cy, r, t0 = sim.last_collapse
            if sim.turn - t0 < 12:
                pygame.draw.circle(screen, (255, 220, 120),
                                   (sx(cx), sy(cy)), int(r * SCALE), 2)

        # 사체
        for c in sim.carcasses:
            pygame.draw.circle(screen, (150, 60, 60), (sx(c.x), sy(c.y)), 3)

        # ── 동물 그리기 (y 정렬: 뒤→앞) ──
        for a in sorted(sim.animals, key=lambda o: o.y):
            if not a.is_alive:
                continue
            col = SPECIES_COLOR[a.SPECIES]
            r = SPECIES_R[a.SPECIES]
            px, py = sx(a.x), sy(a.y)
            if a.SPECIES == "Krill":
                # 떼 크기에 따라 살짝 크게
                rr = 2 + int(min(3, a.swarm_size / 130))
                pygame.draw.circle(screen, col, (px, py), rr)
            elif a.SPECIES == "Orca":
                pygame.draw.ellipse(screen, col, (px - r, py - r // 2, r * 2, r))
                pygame.draw.circle(screen, (240, 240, 245),
                                   (px + a.facing * 3, py), 2)
            elif a.SPECIES == "Penguin":
                pygame.draw.circle(screen, col, (px, py), r)
                pygame.draw.circle(screen, (240, 240, 245), (px, py + 1), 2)
            else:
                pygame.draw.circle(screen, col, (px, py), r)
                # 배고프면 살짝 붉게 표시
                if a.hunger > 80:
                    pygame.draw.circle(screen, C_RED, (px, py), r, 1)

        # ── UI 패널 ──
        pygame.draw.rect(screen, C_PANEL, (sw, 0, UI_W, sh))
        x0 = sw + 18
        screen.blit(f_bg.render("극지방 생태계", True, C_TITLE), (x0, 16))
        screen.blit(f_sm.render(f"턴: {sim.turn}", True, C_TEXT), (x0, 52))
        spd = "4x" if fast else "1x"
        st = "일시정지" if paused else f"진행 {spd}"
        screen.blit(f_sm.render(st, True, C_GREEN), (x0 + 140, 52))

        c = sim.counts()
        y = 86
        screen.blit(f_md.render("개체수", True, C_TITLE), (x0, y)); y += 26
        for sp in ORDER:
            col = SPECIES_COLOR[sp]
            co = col if sp != "Orca" else (90, 120, 170)
            pygame.draw.circle(screen, co, (x0 + 7, y + 8), 6)
            txt = f"{KOR[sp]}"
            screen.blit(f_sm.render(txt, True, C_TEXT), (x0 + 22, y))
            screen.blit(f_sm.render(str(c[sp]), True, C_TEXT), (x0 + 150, y))
            # 막대
            mx = 90
            bw = int(min(1.0, c[sp] / 80) * mx)
            pygame.draw.rect(screen, (60, 70, 88),
                             (x0 + 180, y + 3, mx, 9))
            pygame.draw.rect(screen, co, (x0 + 180, y + 3, bw, 9))
            y += 22

        y += 6
        bm = sim.krill_biomass()
        screen.blit(f_sm.render(f"크릴 바이오매스: {bm:.0f}/{int(6000)}",
                                True, (250, 160, 120)), (x0, y)); y += 20
        screen.blit(f_sm.render(f"이끼(이용가능): {sim.lichen:.0f}",
                                True, C_GREEN), (x0, y)); y += 22
        # 기후(지구 온난화) 상태
        warm = sim.warming
        wcol = (255, 150, 120) if warm > 1.5 else (180, 200, 230)
        screen.blit(f_sm.render(f"온난화: +{warm:.1f}   수온: {sim.terrain.water_temp:.1f}",
                                True, wcol), (x0, y)); y += 20
        screen.blit(f_sm.render(f"빙하 비율: {sim.terrain.ice_fraction()*100:.0f}%",
                                True, (200, 225, 245)), (x0, y)); y += 26

        screen.blit(f_md.render("이벤트 로그", True, C_TITLE), (x0, y)); y += 24
        for line in sim.log[-6:]:
            screen.blit(f_sm.render(line[:26], True, (210, 210, 220)),
                        (x0, y)); y += 18

        # 조작 안내
        y = sh - 92
        for k, v in [("ESC", "종료"), ("Space", "일시정지"),
                     ("F", "4배속"), ("M", "온난화 +3 (가속)")]:
            screen.blit(f_sm.render(k, True, (250, 220, 120)), (x0, y))
            screen.blit(f_sm.render(v, True, C_TEXT), (x0 + 70, y))
            y += 20

        # 종료 화면
        if not sim.running:
            ov = pygame.Surface((sw + UI_W, sh), pygame.SRCALPHA)
            ov.fill((20, 0, 0, 180))
            screen.blit(ov, (0, 0))
            t = f_bg.render("시뮬레이션 종료", True, (255, 210, 210))
            screen.blit(t, ((sw + UI_W) // 2 - t.get_width() // 2, sh // 2 - 40))
            reason = sim.end_reason or "종료"
            t2 = f_md.render(reason[:34], True, (255, 190, 190))
            screen.blit(t2, ((sw + UI_W) // 2 - t2.get_width() // 2, sh // 2))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
