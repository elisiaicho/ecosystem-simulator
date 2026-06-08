"""
viz.py
------
pygame 실시간 시각화 (담당: 1210 이강희)

[카메라 스크롤 구조]
- 맵 전체(WORLD_W x WORLD_H)는 큰 가상 캔버스에 그려진다.
- 화면에는 그 중 VIEW_W x VIEW_H 영역만 보인다 (뷰포트).
- cam_x, cam_y: 뷰포트 좌상단이 월드 좌표계에서 어디 있는지.

조작:
  ESC         종료
  Space       일시정지/재개
  F           4배속 토글
  M           온난화 +3
  방향키/WASD  카메라 이동
  마우스 휠    카메라 이동 (상하)
  Shift+휠    카메라 이동 (좌우)
"""

import pygame
import os
import math
import time

# ── 화면 배치 ──────────────────────────────────────────────────────────────
SCALE    = 8        # 시뮬 1칸 = 8픽셀
UI_W     = 300      # 우측 UI 패널 너비
VIEW_W   = 1280     # 뷰포트 너비 (픽셀)
VIEW_H   = 720      # 뷰포트 높이 (픽셀)
CAM_SPEED = 25      # 키보드 카메라 이동 속도 (픽셀/프레임)
SCROLL_SPD = 40     # 마우스 휠 스크롤 속도

C_ICE   = (224, 236, 246)
C_SEA   = (28,  74, 122)
C_PANEL = (24,  28,  38)
C_TEXT  = (232, 236, 242)
C_TITLE = (150, 205, 255)
C_RED   = (224,  96,  96)
C_GREEN = (120, 210, 140)

SPECIES_COLOR = {
    "PolarBear": (248, 248, 250),
    "ArcticFox": (226, 206, 170),
    "Penguin":   ( 32,  34,  44),
    "Seal":      (120, 120, 132),
    "Orca":      ( 16,  18,  30),
    "ArcticCod": (176, 188, 206),
    "Krill":     (250, 132,  92),
    "Reindeer":  (122,  86,  56),
}
SPECIES_R = {
    "PolarBear": 7, "ArcticFox": 6, "Penguin": 7, "Seal": 5,
    "Orca": 10, "ArcticCod": 5, "Krill": 3, "Reindeer": 7,
}
IMG_SCALE = 1 / 4
ORDER = ["Krill", "ArcticCod", "Reindeer", "Penguin",
         "Seal", "Orca", "PolarBear", "ArcticFox"]
KOR = {
    "PolarBear": "북극곰", "ArcticFox": "북극여우", "Penguin": "펭귄",
    "Seal": "바다표범", "Orca": "범고래",  "ArcticCod": "북극대구",
    "Krill": "크릴",    "Reindeer": "순록",
}

# ── 스프라이트 ──────────────────────────────────────────────────────────────
ANIMAL_SPRITES = {}

ASSET_FILENAMES = {
    "PolarBear": ("polarbear_right.png",  "polarbear_left.png"),
    "ArcticFox": ("arcticfox_right.png",  "arcticfox_left.png"),
    "Penguin":   ("penguin_right.png",    "penguin_left.png"),
    "Seal":      ("seal_right.png",       "seal_left.png"),
    "Orca":      ("orca_right.png",       "orca_left.png"),
    "ArcticCod": ("arcticcod_right.png",  "arcticcod_left.png"),
    "Krill":     ("krill_right.png",      "krill_left.png"),
    "Reindeer":  ("reindeer_right.png",   "reindeer_left.png"),
}


def _load_img(path, target_h):
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * target_h / h), target_h))


def load_animal_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for sp, (fname_r, fname_l) in ASSET_FILENAMES.items():
        r        = SPECIES_R[sp]
        target_h = max(4, int(r * SCALE * 2.5 * IMG_SCALE))
        try:
            path_r    = os.path.join(base_dir, "assets", fname_r)
            path_l    = os.path.join(base_dir, "assets", fname_l)
            img_right = _load_img(path_r, target_h)
            img_left  = _load_img(path_l, target_h)
            img_dead  = pygame.transform.rotate(img_right, 90)
            ANIMAL_SPRITES[sp] = {"right": img_right,
                                  "left":  img_left,
                                  "dead":  img_dead}
            print(f"[이미지 로드] {sp} ✓")
        except Exception as e:
            print(f"[오류] {sp} 이미지 로드 실패: {e}")


# ── 좌표 변환 헬퍼 ──────────────────────────────────────────────────────────
def world_to_screen(wx, wy, cam_x, cam_y):
    """월드 좌표 → 화면(뷰포트) 좌표"""
    return int(wx * SCALE - cam_x), int(wy * SCALE - cam_y)

def is_in_view(px, py, margin=20):
    """화면 안에 있는지 (마진 포함)"""
    return -margin <= px <= VIEW_W + margin and -margin <= py <= VIEW_H + margin


# ── 메인 루프 ───────────────────────────────────────────────────────────────
def run_with_pygame(sim):
    pygame.init()
    screen = pygame.display.set_mode((VIEW_W + UI_W, VIEW_H))
    pygame.display.set_caption("극지방의 아이들 — 생태계 시뮬레이션")
    clock = pygame.time.Clock()

    load_animal_assets()

    def font(sz, bold=False):
        try:
            return pygame.font.SysFont(
                "malgungothic,applegothic,notosanscjk", sz, bold=bold)
        except Exception:
            return pygame.font.Font(None, sz)

    f_sm, f_md, f_bg = font(15), font(18, True), font(26, True)

    # ── 카메라 초기 위치 (맵 중앙) ────────────────────────────────────────
    map_pw = sim.world_w * SCALE   # 맵 전체 픽셀 너비
    map_ph = sim.world_h * SCALE   # 맵 전체 픽셀 높이
    cam_x  = max(0, map_pw // 2 - VIEW_W // 2)
    cam_y  = max(0, map_ph // 2 - VIEW_H // 2)

    def clamp_cam():
        nonlocal cam_x, cam_y
        cam_x = max(0, min(cam_x, map_pw - VIEW_W))
        cam_y = max(0, min(cam_y, map_ph - VIEW_H))

    fast           = False
    paused         = False
    running        = True
    selected_animal = None
    local_effects  = []

    # 뷰포트 서피스 (UI 패널과 분리)
    view_surf = pygame.Surface((VIEW_W, VIEW_H))

    while running:
        # ── 이벤트 ────────────────────────────────────────────────────────
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if   e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_SPACE:  paused  = not paused
                elif e.key == pygame.K_f:      fast    = not fast
                elif e.key == pygame.K_m:      sim.warming += 3.0

            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    # 클릭 좌표를 월드 좌표로 변환해서 동물 선택
                    mx, my = e.pos
                    if mx < VIEW_W:   # UI 패널 클릭은 무시
                        wx = (mx + cam_x) / SCALE
                        wy = (my + cam_y) / SCALE
                        selected_animal = None
                        for a in sim.animals:
                            if a.is_alive and math.hypot(a.x - wx, a.y - wy) < 1.5:
                                selected_animal = a
                                break

                elif e.button == 4:  # 휠 위
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        cam_x -= SCROLL_SPD
                    else:
                        cam_y -= SCROLL_SPD
                    clamp_cam()

                elif e.button == 5:  # 휠 아래
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        cam_x += SCROLL_SPD
                    else:
                        cam_y += SCROLL_SPD
                    clamp_cam()

        # ── 키보드 카메라 이동 (매 프레임) ────────────────────────────────
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: cam_x -= CAM_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: cam_x += CAM_SPEED
        if keys[pygame.K_UP]    or keys[pygame.K_w]: cam_y -= CAM_SPEED
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: cam_y += CAM_SPEED
        clamp_cam()

        # ── 시뮬 진행 ──────────────────────────────────────────────────────
        if not paused and sim.running:
            steps = 4 if fast else 1
            for _ in range(steps):
                if sim.running:
                    sim.step()

        # ══════════════════════════════════════════════════════════════════
        #  뷰포트 렌더링 (view_surf에 그린 뒤 screen에 blit)
        # ══════════════════════════════════════════════════════════════════

        # ── 배경: 빙하 격자 ───────────────────────────────────────────────
        terr   = sim.terrain
        cw, ch = terr.cell_w * SCALE, terr.cell_h * SCALE
        wt     = terr.water_temp
        warm_f = max(0.0, min(1.0, (wt + 1.0) / 10.0))
        sea_col = (
            int(C_SEA[0] + warm_f * 90),
            int(C_SEA[1] + warm_f * 20),
            int(C_SEA[2] - warm_f * 60),
        )

        # 카메라 범위에 해당하는 격자 셀만 그림 (렉 방지)
        gx_start = max(0, int(cam_x / cw) - 1)
        gx_end   = min(terr.grid_w, int((cam_x + VIEW_W) / cw) + 2)
        gy_start = max(0, int(cam_y / ch) - 1)
        gy_end   = min(terr.grid_h, int((cam_y + VIEW_H) / ch) + 2)

        for gx in range(gx_start, gx_end):
            for gy in range(gy_start, gy_end):
                rx = int(gx * cw - cam_x)
                ry = int(gy * ch - cam_y)
                color = C_ICE if terr.ice[gx][gy] else sea_col
                pygame.draw.rect(view_surf, color,
                                 (rx, ry, int(cw) + 1, int(ch) + 1))

        # ── 빙하 붕괴 표시 ────────────────────────────────────────────────
        if sim.last_collapse:
            cx, cy, r, t0 = sim.last_collapse
            if sim.turn - t0 < 12:
                px, py = world_to_screen(cx, cy, cam_x, cam_y)
                if is_in_view(px, py, int(r * SCALE)):
                    pygame.draw.circle(view_surf, (255, 220, 120),
                                       (px, py), int(r * SCALE), 2)

        # ── 사체 ──────────────────────────────────────────────────────────
        # scavenging 중인 여우 → 가장 가까운 사체 매핑
        fox_on_carcass = {}
        for a in sim.animals:
            if a.is_alive and a.SPECIES == "ArcticFox" and getattr(a, "state", "") == "scavenging":
                nc = min(sim.carcasses,
                         key=lambda c: math.hypot(c.x - a.x, c.y - a.y),
                         default=None)
                if nc is not None and math.hypot(nc.x - a.x, nc.y - a.y) < 6:
                    fox_on_carcass[id(nc)] = a

        for c in sim.carcasses:
            px, py = world_to_screen(c.x, c.y, cam_x, cam_y)
            if not is_in_view(px, py): continue
            pygame.draw.line(view_surf, (180, 60, 60), (px-3, py-3), (px+3, py+3), 2)
            pygame.draw.line(view_surf, (180, 60, 60), (px+3, py-3), (px-3, py+3), 2)
            if id(c) in fox_on_carcass:
                fox   = fox_on_carcass[id(c)]
                fsprite = ANIMAL_SPRITES.get("ArcticFox")
                if fsprite:
                    img  = fsprite["right"] if fox.facing >= 0 else fsprite["left"]
                    rect = img.get_rect(midbottom=(px, py + 4))
                    view_surf.blit(img, rect)
                else:
                    pygame.draw.circle(view_surf, (226, 206, 170), (px, py - 6), 4)

        # ── 동물 그리기 (y 정렬) ──────────────────────────────────────────
        for a in sorted(sim.animals, key=lambda o: o.y):
            if not a.is_alive:
                continue
            px, py = world_to_screen(a.x, a.y, cam_x, cam_y)
            if not is_in_view(px, py):
                continue

            r           = SPECIES_R[a.SPECIES]
            sprite_data = ANIMAL_SPRITES.get(a.SPECIES)

            if sprite_data:
                img  = sprite_data["right"] if a.facing >= 0 else sprite_data["left"]
                rect = img.get_rect(center=(px, py))
                view_surf.blit(img, rect)
            else:
                col = SPECIES_COLOR[a.SPECIES]
                pygame.draw.circle(view_surf, col, (px, py), r)
                if a.hunger > 80:
                    pygame.draw.circle(view_surf, C_RED, (px, py), r, 1)

            # 선택된 동물 강조
            if a is selected_animal:
                pygame.draw.circle(view_surf, C_GREEN, (px, py), r + 5, 2)

            # ── 행동 시각화 ────────────────────────────────────────────────
            state = getattr(a, "state", "idle")
            if state == "hunting":
                pygame.draw.polygon(view_surf, (255, 160, 40), [
                    (px + r + 1, py - r - 2),
                    (px + r + 5, py - r - 5),
                    (px + r + 1, py - r - 8),
                ])
            elif state == "fleeing":
                for i in range(3):
                    ox = px - r - 2 - i * 3
                    pygame.draw.circle(view_surf, (100, 180, 255),
                                       (ox, py - r - 3), 1)
            elif state == "scavenging":
                pygame.draw.line(view_surf, (160, 100, 40),
                                 (px - 3, py - r - 7), (px + 3, py - r - 3), 2)
                pygame.draw.line(view_surf, (160, 100, 40),
                                 (px + 3, py - r - 7), (px - 3, py - r - 3), 2)
            elif state == "eating":
                pygame.draw.line(view_surf, C_GREEN,
                                 (px, py - r - 7), (px, py - r - 3), 2)
                pygame.draw.line(view_surf, C_GREEN,
                                 (px - 2, py - r - 5), (px + 2, py - r - 5), 2)

            # 범고래 음파 링
            if a.SPECIES == "Orca":
                ring_timer = getattr(a, "echo_ring", 0)
                if ring_timer > 0:
                    ring_radius = int((20 - ring_timer) * 4)
                    pygame.draw.circle(view_surf, (150, 220, 255),
                                       (px, py), ring_radius, 1)
                    a.echo_ring -= 5

        # ── 이펙트 ────────────────────────────────────────────────────────
        if hasattr(sim, "visual_effects"):
            while sim.visual_effects:
                eff_type, ex, ey = sim.visual_effects.pop(0)
                local_effects.append({
                    "type": eff_type, "wx": ex, "wy": ey,
                    "start_time": time.time()
                })

        now = time.time()
        remaining = []
        for eff in local_effects:
            dt = now - eff["start_time"]
            if dt > 0.6:
                continue
            progress = dt / 0.6
            ex, ey = world_to_screen(eff["wx"], eff["wy"], cam_x, cam_y)
            if eff["type"] == "hunt":
                for i in range(6):
                    ang  = i * (math.pi / 3)
                    dist = progress * 20
                    pygame.draw.circle(view_surf, C_RED,
                                       (int(ex + math.cos(ang) * dist),
                                        int(ey + math.sin(ang) * dist)),
                                       max(1, int(4 * (1 - progress))))
            elif eff["type"] == "reproduction":
                up_y = ey - int(progress * 25)
                try:
                    heart = f_sm.render("♥", True, (255, 130, 190))
                    view_surf.blit(heart, (ex - 5, up_y - 5))
                except Exception:
                    pygame.draw.circle(view_surf, (255, 130, 190), (ex, up_y), 5)
            remaining.append(eff)
        local_effects = remaining

        # ── 미니맵 (뷰포트 좌하단) ────────────────────────────────────────
        mm_w, mm_h = 160, 90
        mm_x, mm_y = 10, VIEW_H - mm_h - 10
        mm_surf = pygame.Surface((mm_w, mm_h))
        mm_surf.set_alpha(200)
        mm_surf.fill((10, 20, 40))
        # 빙하 셀 점으로 표시
        for (ix, iy) in terr.ice_cells:
            mx2 = int(ix / sim.world_w * mm_w)
            my2 = int(iy / sim.world_h * mm_h)
            if 0 <= mx2 < mm_w and 0 <= my2 < mm_h:
                mm_surf.set_at((mx2, my2), C_ICE)
        # 동물 점
        for a in sim.animals:
            if not a.is_alive: continue
            mx2 = int(a.x / sim.world_w * mm_w)
            my2 = int(a.y / sim.world_h * mm_h)
            if 0 <= mx2 < mm_w and 0 <= my2 < mm_h:
                col = SPECIES_COLOR.get(a.SPECIES, (200, 200, 200))
                mm_surf.set_at((mx2, my2), col)
        # 현재 뷰포트 사각형
        vx1 = int(cam_x / map_pw * mm_w)
        vy1 = int(cam_y / map_ph * mm_h)
        vx2 = int((cam_x + VIEW_W) / map_pw * mm_w)
        vy2 = int((cam_y + VIEW_H) / map_ph * mm_h)
        pygame.draw.rect(mm_surf, (255, 255, 100),
                         (vx1, vy1, max(2, vx2 - vx1), max(2, vy2 - vy1)), 1)
        view_surf.blit(mm_surf, (mm_x, mm_y))
        pygame.draw.rect(view_surf, C_TITLE, (mm_x, mm_y, mm_w, mm_h), 1)

        # ── 선택된 동물 정보창 ────────────────────────────────────────────
        if selected_animal and selected_animal.is_alive:
            get_hp     = lambda a: getattr(a, "_Animal__hp",     getattr(a, "hp",     100))
            get_hunger = lambda a: getattr(a, "_Animal__hunger", getattr(a, "hunger",   0))
            bx, by, bw, bh = 15, 15, 190, 155
            info = pygame.Surface((bw, bh))
            info.set_alpha(210)
            info.fill((22, 26, 36))
            view_surf.blit(info, (bx, by))
            pygame.draw.rect(view_surf, C_TITLE, (bx, by, bw, bh), 1)
            lines = [
                f" 종류: {selected_animal.SPECIES}",
                f" 성별: {'수컷(M)' if selected_animal.gender == 'M' else '암컷(F)'}",
                f" 나이: {selected_animal.age}",
                f" 체력: {int(get_hp(selected_animal))}",
                f" 허기: {int(get_hunger(selected_animal))}",
                f" 상태: {selected_animal.state}",
                f" 서식지: {'빙하위' if sim.terrain.is_ice_at(selected_animal.x, selected_animal.y) else '바다위'}",
            ]
            ty = by + 12
            for line in lines:
                color = C_RED if "체력" in line and get_hp(selected_animal) < 30 else C_TEXT
                view_surf.blit(f_sm.render(line, True, color), (bx + 8, ty))
                ty += 20

        # ── 카메라 위치 표시 (좌상단) ─────────────────────────────────────
        cam_info = f"카메라: ({int(cam_x/SCALE)}, {int(cam_y/SCALE)})  WASD/방향키 이동 | 휠 스크롤"
        view_surf.blit(f_sm.render(cam_info, True, (180, 180, 200)), (mm_x, VIEW_H - mm_h - 25))

        # view_surf → screen
        screen.blit(view_surf, (0, 0))

        # ══════════════════════════════════════════════════════════════════
        #  UI 패널 (카메라와 무관하게 고정)
        # ══════════════════════════════════════════════════════════════════
        pygame.draw.rect(screen, C_PANEL, (VIEW_W, 0, UI_W, VIEW_H))
        x0 = VIEW_W + 18

        screen.blit(f_bg.render("극지방 생태계", True, C_TITLE), (x0, 16))
        screen.blit(f_sm.render(f"턴: {sim.turn}", True, C_TEXT), (x0, 52))
        spd = "4x" if fast else "1x"
        st  = "일시정지" if paused else f"진행 {spd}"
        screen.blit(f_sm.render(st, True, C_GREEN), (x0 + 140, 52))

        c = sim.counts()
        y = 86
        screen.blit(f_md.render("개체수", True, C_TITLE), (x0, y)); y += 26
        for sp in ORDER:
            col = SPECIES_COLOR[sp]
            co  = (90, 120, 170) if sp == "Orca" else col
            pygame.draw.circle(screen, co, (x0 + 7, y + 8), 6)
            screen.blit(f_sm.render(KOR[sp],    True, C_TEXT), (x0 + 22,  y))
            screen.blit(f_sm.render(str(c[sp]), True, C_TEXT), (x0 + 150, y))
            bw2 = int(min(1.0, c[sp] / 80) * 90)
            pygame.draw.rect(screen, (60, 70, 88), (x0 + 180, y + 3, 90, 9))
            pygame.draw.rect(screen, co,           (x0 + 180, y + 3, bw2, 9))
            y += 22

        y += 6
        bm = sim.krill_biomass()
        screen.blit(f_sm.render(f"크릴 바이오매스: {bm:.0f}/6000",
                                True, (250, 160, 120)), (x0, y)); y += 20
        screen.blit(f_sm.render(f"이끼(이용가능): {sim.lichen:.0f}",
                                True, C_GREEN), (x0, y)); y += 22

        warm = sim.warming
        wcol = (255, 150, 120) if warm > 1.5 else (180, 200, 230)
        screen.blit(f_sm.render(
            f"온난화: +{warm:.1f}   수온: {sim.terrain.water_temp:.1f}",
            True, wcol), (x0, y)); y += 20
        screen.blit(f_sm.render(
            f"빙하 비율: {sim.terrain.ice_fraction()*100:.0f}%",
            True, (200, 225, 245)), (x0, y)); y += 26

        screen.blit(f_md.render("이벤트 로그", True, C_TITLE), (x0, y)); y += 24
        for line in sim.log[-6:]:
            screen.blit(f_sm.render(line[:26], True, (210, 210, 220)),
                        (x0, y)); y += 18

        y = VIEW_H - 100
        for k, v in [("ESC", "종료"), ("Space", "일시정지"),
                     ("F", "4배속"), ("M", "온난화 +3"),
                     ("WASD/방향키", "카메라 이동"), ("휠", "스크롤"),
                     ("Shift+휠", "좌우 스크롤")]:
            screen.blit(f_sm.render(k, True, (250, 220, 120)), (x0, y))
            screen.blit(f_sm.render(v, True, C_TEXT),           (x0 + 90, y))
            y += 18

        # ── 종료 오버레이 ─────────────────────────────────────────────────
        if not sim.running:
            ov = pygame.Surface((VIEW_W + UI_W, VIEW_H), pygame.SRCALPHA)
            ov.fill((20, 0, 0, 180))
            screen.blit(ov, (0, 0))
            t  = f_bg.render("시뮬레이션 종료", True, (255, 210, 210))
            t2 = f_md.render((sim.end_reason or "종료")[:34],
                             True, (255, 190, 190))
            screen.blit(t,  ((VIEW_W + UI_W) // 2 - t.get_width()  // 2, VIEW_H // 2 - 40))
            screen.blit(t2, ((VIEW_W + UI_W) // 2 - t2.get_width() // 2, VIEW_H // 2))

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
