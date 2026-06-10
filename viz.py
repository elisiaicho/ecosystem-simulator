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
  Y           줌 (확대/축소)
  방향키/WASD  카메라 이동
  마우스 휠    카메라 이동 (상하)
  Shift+휠    카메라 이동 (좌우)
"""

import pygame
import os
import math
import time
from viz_manager import VisualManager

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
    "PolarBear": 10.5, "ArcticFox": 9, "Penguin": 10.5, "Seal": 7.5,
    "Orca": 15, "ArcticCod": 7.5, "Krill": 4.5, "Reindeer": 10.5,
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
SHINY_PENGUIN_SPRITES = []

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
SHINY_PENGUIN_FILENAMES = [("penguin_shiny1_right.png","penguin_shiny1_left.png"),
                           ("penguin_shiny2_right.png","penguin_shiny2_left.png")
                           ]

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
        except Exception as e:
            pass
    # ── 이로치 펭귄 스프라이트 로드 ──────────────────────────
    SHINY_PENGUIN_SPRITES.clear()
    large_size = int(SCALE * 10)

    for fname_r, fname_l in SHINY_PENGUIN_FILENAMES:
        try:
            path_r = os.path.join(base_dir, "assets", fname_r)
            path_l = os.path.join(base_dir, "assets", fname_l)

            img_r = pygame.image.load(path_r).convert_alpha()
            img_l = pygame.image.load(path_l).convert_alpha()

            img_r = pygame.transform.scale(img_r, (large_size, large_size))
            img_l = pygame.transform.scale(img_l, (large_size, large_size))

            SHINY_PENGUIN_SPRITES.append({
                "right": img_r,
                "left": img_l,
                "dead": pygame.transform.rotate(img_r, 90)
            })

            print(f"[로드 성공] {fname_r}")

        except Exception as e:
           print(f"[로드 실패] {fname_r}: {e}")      

# ── 좌표 변환 헬퍼 ──────────────────────────────────────────────────────────
def world_to_screen(wx, wy, cam_x, cam_y):
    """월드 좌표 → 화면(뷰포트) 좌표"""
    return int(wx * SCALE - cam_x), int(wy * SCALE - cam_y)

def is_in_view(px, py, margin=20):
    """화면 안에 있는지 (마진 포함)"""
    return -margin <= px <= VIEW_W + margin and -margin <= py <= VIEW_H + margin


# ── 메인 루프 ───────────────────────────────────────────────────────────────
def run_with_pygame(sim):
    global SCALE
    pygame.init()
    screen = pygame.display.set_mode((VIEW_W + UI_W, VIEW_H))
    pygame.display.set_caption("극지방의 아이들 — 생태계 시뮬레이션")
    clock = pygame.time.Clock()

    load_animal_assets()

    # VisualManager 초기화 (사냥/번식 이펙트 + 클릭 상태창)
    vis_manager = VisualManager(screen, sim)

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
        nonlocal cam_x, cam_y, map_pw, map_ph
        cam_x = max(0, min(cam_x, map_pw - VIEW_W))
        cam_y = max(0, min(cam_y, map_ph - VIEW_H))

    fast           = False
    paused         = False
    running        = True
    show_event_log = False
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
                elif e.key == pygame.K_l:      show_event_log = not show_event_log
                elif e.key == pygame.K_m:      sim.warming += 3.0
                
                # --- Y키 줌 토글 ---
                elif e.key == pygame.K_y:
                    old_scale = SCALE
                    SCALE = 4 if SCALE == 8 else 8
                    
                    # 1. 스케일 변경에 따라 맵 전체 크기를 갱신 (이게 없으면 시야가 꼬임)
                    map_pw = sim.world_w * SCALE
                    map_ph = sim.world_h * SCALE
                    
                    # 2. 이미지 크기 재조정
                    load_animal_assets()
                    
                    # 3. 화면 중앙 좌표 유지
                    center_wx = (cam_x + VIEW_W / 2) / old_scale
                    center_wy = (cam_y + VIEW_H / 2) / old_scale
                    cam_x = center_wx * SCALE - VIEW_W / 2
                    cam_y = center_wy * SCALE - VIEW_H / 2
                    
                    # 4. 카메라 위치 제한 (안에 sim이 들어가면 에러가 나므로 지웠습니다!)
                    clamp_cam()

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
                        # VisualManager에도 선택 동물 동기화
                        vis_manager.selected_animal = selected_animal

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

        # ── 빙하 붕괴 표시 (파티클 + 진동) ─────────────────────────────
        if sim.last_collapse:
            cx, cy, r, t0 = sim.last_collapse
            age = sim.turn - t0
            if age == 0:
                # 붕괴 발생 순간: 파티클 이펙트를 local_effects에 등록
                import random as _rnd
                px0, py0 = world_to_screen(cx, cy, cam_x, cam_y)
                particles = []
                for _ in range(22):
                    ang  = _rnd.uniform(0, 2 * math.pi)
                    spd  = _rnd.uniform(0.4, 1.2)
                    size = _rnd.randint(2, 5)
                    particles.append({
                        "ox": cx, "oy": cy,
                        "vx": math.cos(ang) * spd * r,
                        "vy": math.sin(ang) * spd * r,
                        "size": size,
                    })
                local_effects.append({
                    "type": "collapse",
                    "wx": cx, "wy": cy, "r": r,
                    "particles": particles,
                    "start_time": time.time(),
                })
            elif age < 14:
                # 진동: 붕괴 후 몇 턴간 원이 흔들리며 희미해짐
                px, py = world_to_screen(cx, cy, cam_x, cam_y)
                if is_in_view(px, py, int(r * SCALE)):
                    fade   = max(0, 255 - age * 18)
                    shake  = int(math.sin(age * 2.8) * 3)
                    col    = (255, max(80, 220 - age * 12), 80)
                    surf_c = pygame.Surface((int(r * SCALE * 2 + 10),
                                            int(r * SCALE * 2 + 10)),
                                           pygame.SRCALPHA)
                    ctr    = (int(r * SCALE) + 5 + shake, int(r * SCALE) + 5)
                    pygame.draw.circle(surf_c, (*col, fade),
                                       ctr, int(r * SCALE), max(1, 3 - age // 4))
                    view_surf.blit(surf_c,
                                   (px - int(r * SCALE) - 5,
                                    py - int(r * SCALE) - 5))

        # ── 사체 ──────────────────────────────────────────────────────────
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

        # ── 상호작용 시각화 (동물 본체보다 먼저 그려 겹침 방지) ───────────
        # 1) ArcticFox → PolarBear follow 선: scavenging 상태 여우가 곰 추적 중임을 표시
        bears_pos = {id(a): world_to_screen(a.x, a.y, cam_x, cam_y)
                     for a in sim.animals if a.is_alive and a.SPECIES == "PolarBear"}
        for a in sim.animals:
            if not a.is_alive or a.SPECIES != "ArcticFox":
                continue
            if getattr(a, "state", "") != "scavenging":
                continue
            # 시야 내 가장 가까운 곰 찾기
            fx, fy = world_to_screen(a.x, a.y, cam_x, cam_y)
            nearest_bear_px = None
            best_d = 999999
            for bid, bpos in bears_pos.items():
                d = math.hypot(fx - bpos[0], fy - bpos[1])
                if d < best_d:
                    best_d, nearest_bear_px = d, bpos
            if nearest_bear_px and best_d < 200:
                # 점선: 3픽셀 간격으로 끊어 그림
                bx2, by2 = nearest_bear_px
                seg_len, gap = 4, 4
                total = math.hypot(bx2 - fx, by2 - fy)
                if total > 1e-9:
                    dx, dy = (bx2 - fx) / total, (by2 - fy) / total
                    t = 0
                    draw = True
                    while t < total:
                        if draw:
                            x1 = int(fx + dx * t)
                            y1 = int(fy + dy * t)
                            x2 = int(fx + dx * min(t + seg_len, total))
                            y2 = int(fy + dy * min(t + seg_len, total))
                            pygame.draw.line(view_surf, (200, 140, 60), (x1, y1), (x2, y2), 1)
                        t += seg_len + gap
                        draw = not draw

        # 2) ArcticCod school_move: fleeing 상태 대구끼리 가는 선으로 무리 연결
        fleeing_cods = [a for a in sim.animals
                        if a.is_alive and a.SPECIES == "ArcticCod"
                        and getattr(a, "state", "") == "fleeing"]
        if len(fleeing_cods) >= 2:
            # 인접한 대구 쌍만 연결 (거리 12 이내)
            for i, ca in enumerate(fleeing_cods):
                pax, pay = world_to_screen(ca.x, ca.y, cam_x, cam_y)
                if not is_in_view(pax, pay):
                    continue
                for cb in fleeing_cods[i+1:]:
                    if math.hypot(ca.x - cb.x, ca.y - cb.y) > 12:
                        continue
                    pbx, pby = world_to_screen(cb.x, cb.y, cam_x, cam_y)
                    if not is_in_view(pbx, pby):
                        continue
                    pygame.draw.line(view_surf, (80, 140, 200),
                                     (pax, pay), (pbx, pby), 1)

        # ── 동물 그리기 (y 정렬) ──────────────────────────────────────────
        for a in sorted(sim.animals, key=lambda o: o.y):
            if not a.is_alive:
                continue
            px, py = world_to_screen(a.x, a.y, cam_x, cam_y)
            if not is_in_view(px, py):
                continue

            r           = SPECIES_R[a.SPECIES]
            shiny_idx   = getattr(a, "shiny_variant", None)   # 이로치 번호(0 or 1), 없으면 None
            if shiny_idx is not None and shiny_idx < len(SHINY_PENGUIN_SPRITES):
                sprite_data = SHINY_PENGUIN_SPRITES[shiny_idx]
            else:
                sprite_data = ANIMAL_SPRITES.get(a.SPECIES)

            if sprite_data:
                img  = sprite_data["right"] if a.facing >= 0 else sprite_data["left"]
                rect = img.get_rect(center=(px, py))
                view_surf.blit(img, rect)
            else:
                # fallback: 스프라이트 로드 실패 시 종별 색상 원으로 표시
                col = SPECIES_COLOR.get(a.SPECIES, (200, 200, 200))
                pygame.draw.circle(view_surf, col, (px, py),
                                   max(3, int(SPECIES_R.get(a.SPECIES, 6))))

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
            # collapse는 자체 지속시간(1.2s) 처리, 나머지는 0.6s
            max_dur = 1.2 if eff["type"] == "collapse" else 0.6
            if dt > max_dur:
                continue
            progress = dt / max_dur
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
                    view_surf.blit(heart, (ex - 5, up_y - 10))
                except Exception:
                    pygame.draw.circle(view_surf, (255, 130, 190), (ex, up_y), 5)
            elif eff["type"] == "collapse":
                # 파티클: 각 조각이 바깥으로 날아가며 작아지고 희미해짐
                for p in eff["particles"]:
                    ppx = int((eff["wx"] + p["vx"] * progress * 3) * SCALE - cam_x)
                    ppy = int((eff["wy"] + p["vy"] * progress * 3) * SCALE - cam_y)
                    if not is_in_view(ppx, ppy, 20):
                        continue
                    alpha = int(255 * (1 - progress))
                    size  = max(1, int(p["size"] * (1 - progress * 0.7)))
                    frac  = progress
                    pcol  = (
                        int(200 + 55 * (1 - frac)),
                        int(220 + 35 * (1 - frac)),
                        255,
                    )
                    psurf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                    pygame.draw.circle(psurf, (*pcol, alpha), (size + 1, size + 1), size)
                    view_surf.blit(psurf, (ppx - size - 1, ppy - size - 1))
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
        cam_info = f"카메라: ({int(cam_x/SCALE)}, {int(cam_y/SCALE)})  WASD 이동 | Y 줌 토글 | 휠 스크롤"
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
        K_MAP = {
            "PolarBear": 8,  "ArcticFox": 18, "Penguin": 38, "Seal": 32,
            "Orca": 8,       "ArcticCod": 80, "Krill": 60,   "Reindeer": 28
                    }
        for sp in ORDER:
            col = SPECIES_COLOR[sp]
            co  = (90, 120, 170) if sp == "Orca" else col
            pygame.draw.circle(screen, co, (x0 + 7, y + 8), 6)
            screen.blit(f_sm.render(KOR[sp],    True, C_TEXT), (x0 + 22,  y))
            screen.blit(f_sm.render(str(c[sp]), True, C_TEXT), (x0 + 150, y))
            bw2 = int(min(1.0, c[sp] / K_MAP[sp]) * 90)
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
        for line in sim.log[-4:]:
            screen.blit(f_sm.render(line[:26], True, (210, 210, 220)),
                        (x0, y)); y += 18

        if show_event_log:
            overlay_w = VIEW_W - 120
            overlay_h = VIEW_H - 120
            overlay = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
            overlay.fill((12, 16, 26, 220))
            pygame.draw.rect(overlay, (110, 160, 220), (0, 0, overlay_w, overlay_h), 2)
            overlay.blit(f_md.render("Event Log", True, C_TITLE), (18, 16))
            history = getattr(sim, "event_history", [])
            if history:
                oy = 52
                for line in history[-18:]:
                    overlay.blit(f_sm.render(line[:70], True, C_TEXT), (18, oy))
                    oy += 18
            else:
                overlay.blit(f_sm.render("No events recorded yet.", True, C_TEXT), (18, 56))
            screen.blit(overlay, (40, 40))

        # ── 키 안내 패널 ─────────────────────────────────────────────────
        # 섹션 타이틀
        key_section_y = VIEW_H - 215
        screen.blit(f_md.render("키 조작", True, C_TITLE), (x0, key_section_y))
        key_section_y += 22

        # 배경 박스
        key_box_w = UI_W - 30
        key_box_h = 190
        key_bg = pygame.Surface((key_box_w, key_box_h))
        key_bg.set_alpha(140)
        key_bg.fill((18, 22, 34))
        screen.blit(key_bg, (x0 - 4, key_section_y))
        pygame.draw.rect(screen, (60, 80, 120),
                         (x0 - 4, key_section_y, key_box_w, key_box_h), 1)

        KEY_GROUPS = [
            # (카테고리색, [(키라벨, 설명), ...])
            ((120, 200, 255), [
                ("Space",  "일시정지 / 재개"),
                ("F",      "4배속 토글"),
                ("M",      "온난화 +3℃ 강제"),
            ]),
            ((255, 220, 100), [
                ("WASD",   "카메라 이동"),
                ("휠",     "위아래 스크롤"),
                ("Shift+휠","좌우 스크롤"),
                ("Y",      "줌 확대/축소"),
            ]),
            ((255, 110, 110), [
                ("ESC",    "시뮬레이션 종료"),
            ]),
        ]

        ky = key_section_y + 8
        for cat_color, entries in KEY_GROUPS:
            for key_label, desc in entries:
                # 키 이름 박스
                label_surf = f_sm.render(key_label, True, (20, 20, 30))
                lw = label_surf.get_width() + 10
                lh = 16
                pygame.draw.rect(screen, cat_color,
                                 (x0, ky, lw, lh), border_radius=3)
                screen.blit(label_surf, (x0 + 5, ky))
                # 설명 텍스트
                screen.blit(f_sm.render(desc, True, C_TEXT), (x0 + lw + 8, ky))
                ky += 19
            ky += 4  # 그룹 사이 여백

        # ── VisualManager 렌더 호출 제거 ──
        # vis_manager.render()는 카메라 오프셋/SCALE 변환 없이 screen에 직접 그려
        # 동물들이 좌상단에 원으로 중복 렌더링되는 버그를 유발하므로 제거.
        # 이펙트는 local_effects, 상태창은 selected_animal 블록에서 이미 처리됨.

        # ── 종료 오버레이 (멸망 애니메이션) ─────────────────────────────────
        if not sim.running:
            # 첫 진입 시점 기록
            if not hasattr(sim, '_end_time'):
                sim._end_time = time.time()
            end_dt = time.time() - sim._end_time

            # 1) 붉게 물드는 배경 (0~2초에 걸쳐 투명도 0→210)
            fade_alpha = min(210, int(end_dt / 2.0 * 210))
            ov = pygame.Surface((VIEW_W + UI_W, VIEW_H), pygame.SRCALPHA)
            ov.fill((30, 0, 0, fade_alpha))
            screen.blit(ov, (0, 0))

            # 2) 균열처럼 보이는 붉은 세로선들 (1초 후 등장, 서서히 늘어남)
            if end_dt > 1.0:
                crack_progress = min(1.0, (end_dt - 1.0) / 2.0)
                import random as _rnd
                _rnd.seed(42)   # 매 프레임 같은 균열 위치 유지
                for _ in range(18):
                    cx2 = _rnd.randint(0, VIEW_W + UI_W)
                    max_len = _rnd.randint(80, VIEW_H)
                    cy2 = _rnd.randint(0, VIEW_H // 2)
                    crack_len = int(max_len * crack_progress)
                    alpha_c = int(180 * crack_progress)
                    cs = pygame.Surface((3, crack_len), pygame.SRCALPHA)
                    cs.fill((255, 60, 60, alpha_c))
                    screen.blit(cs, (cx2, cy2))

            # 3) 텍스트: 1.5초 후 등장, 위에서 내려오며 흔들림
            if end_dt > 1.5:
                txt_progress = min(1.0, (end_dt - 1.5) / 1.2)
                shake_x = int(math.sin(end_dt * 18) * max(0, 5 * (1 - txt_progress)))
                target_y  = VIEW_H // 2 - 50
                start_y   = -60
                title_y   = int(start_y + (target_y - start_y) * txt_progress)
                t  = f_bg.render("생태계 붕괴", True, (255, 200, 200))
                screen.blit(t, ((VIEW_W + UI_W) // 2 - t.get_width() // 2 + shake_x, title_y))

            # 4) 원인 텍스트: 2.5초 후 등장
            # 4) 원인 텍스트: 2.5초 후 등장
            if end_dt > 2.5:
                reason = sim.end_reason or "알 수 없는 원인"
                words = reason.split()
                lines, line = [], ""
                for w in words:
                    if len(line) + len(w) + 1 > 18:
                        lines.append(line)
                        line = w
                    else:
                        line = (line + " " + w).strip()
                if line:
                    lines.append(line)
                for i, ln in enumerate(lines):
                    t2 = f_md.render(ln, True, (255, 170, 170))
                    screen.blit(t2, ((VIEW_W + UI_W) // 2 - t2.get_width() // 2,
                                     VIEW_H // 2 + 10 + i * 26))

            # 5) 재시작/종료 안내: 3초 후 등장
            if end_dt > 3.0:
                hint = f_sm.render("Q / ESC — 종료", True, (200, 200, 200))
                screen.blit(hint, ((VIEW_W + UI_W) // 2 - hint.get_width() // 2,
                                   VIEW_H // 2 + 60))

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
