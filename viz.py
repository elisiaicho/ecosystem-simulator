"""
viz.py
------
pygame 실시간 시각화 (담당: 1210 이강희)

main.py 의 Simulation 을 받아 매 프레임 step() 을 호출하고 그려준다.

조작:
  ESC    종료
  Space  일시정지/재개
  F      빠르게(한 프레임에 여러 step)
  M      온난화 +3 강제 발동
"""

import pygame
import os

# ── 화면 배치 ──────────────────────────────────────────────────────────────
SCALE = 8
UI_W  = 300

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
SPECIES_R = {  # 도형 반지름(픽셀) — 이미지 크기와 fallback 원 크기에 사용
    "PolarBear": 7, "ArcticFox": 6, "Penguin": 7, "Seal": 5,
    "Orca": 10, "ArcticCod": 5, "Krill": 3, "Reindeer": 7,
}
IMG_SCALE = 1 / 7  # 이미지 크기 배율 (1.0 = 기본, 줄이려면 작게)
ORDER = ["Krill", "ArcticCod", "Reindeer", "Penguin",
         "Seal", "Orca", "PolarBear", "ArcticFox"]
KOR = {
    "PolarBear": "북극곰", "ArcticFox": "북극여우", "Penguin": "펭귄",
    "Seal": "바다표범", "Orca": "범고래",  "ArcticCod": "북극대구",
    "Krill": "크릴",    "Reindeer": "순록",
}

# ── 스프라이트 ──────────────────────────────────────────────────────────────
ANIMAL_SPRITES = {}   # species -> {"right": Surface, "left": Surface, "dead": Surface}

# assets 폴더 실제 파일명에 맞춤 (방향별 분리)
ASSET_FILENAMES = {
    "PolarBear": ("polarbear_right.png",  "polarbear_left.png"),
    "ArcticFox": ("arcticfox_right.png",  "arcticfox_left.png"),
    "Penguin":   ("penguin_right.png",     "penguin_left.png"),
    "Seal":      ("seal_right.png",        "seal_left.png"),
    "Orca":      ("orca_right.png",        "orca_left.png"),
    "ArcticCod": ("arcticcod_right.png",  "arcticcod_left.png"),
    "Krill":     ("krill_right.png",       "krill_left.png"),
    "Reindeer":  ("reindeer_right.png",    "reindeer_left.png"),
}


def _load_img(path, target_h):
    """이미지 로드 + 비율 유지 리사이즈."""
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * target_h / h), target_h))


def load_animal_assets():
    """pygame.init() 이후에 호출. viz.py 기준 절대경로로 assets를 찾는다."""
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


# ── 메인 루프 ───────────────────────────────────────────────────────────────
def run_with_pygame(sim):
    pygame.init()
    sw = sim.world_w * SCALE
    sh = sim.world_h * SCALE
    screen = pygame.display.set_mode((sw + UI_W, sh))
    pygame.display.set_caption("극지방의 아이들 — 생태계 시뮬레이션")
    clock = pygame.time.Clock()
    
    # ── 버그 수정: pygame.init() 직후 여기서 호출 ─────────────────────────
    load_animal_assets()

    def font(sz, bold=False):
        try:
            return pygame.font.SysFont(
                "malgungothic,applegothic,notosanscjk", sz, bold=bold)
        except Exception:
            return pygame.font.Font(None, sz)

    f_sm, f_md, f_bg = font(15), font(18, True), font(26, True)

    fast    = False
    paused  = False
    running = True

    def sx(x): return int(x * SCALE)
    def sy(y): return int(y * SCALE)
    selected_animal = None 
    local_effects = []
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
            # ─────────────────────────────────────────────────────────
        # [추가] 마우스 좌클릭 시 해당 위치의 동물 선택
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                selected_animal = None  # 클릭할 때마다 선택 초기화
            
                import math
                for a in sim.animals:
                    if getattr(a, 'is_alive', True):
                        # 동물의 x, y 좌표에 SCALE을 곱해 화면 좌표와 거리 비교
                        if math.hypot(a.x * SCALE - mx, a.y * SCALE - my) < 12:
                            selected_animal = a
                            break
        # ─────────────────────────────────────────────────────────

        # ── 시뮬 진행 ──────────────────────────────────────────────────────
        if not paused and sim.running:
            steps = 4 if fast else 1
            for _ in range(steps):
                if sim.running:
                    sim.step()

        # ── 배경: 동적 빙하 격자 ──────────────────────────────────────────
        terr = sim.terrain
        cw, ch = terr.cell_w * SCALE, terr.cell_h * SCALE
        wt     = terr.water_temp
        warm_f = max(0.0, min(1.0, (wt + 1.0) / 10.0))
        sea_col = (
            int(C_SEA[0] + warm_f * 90),
            int(C_SEA[1] + warm_f * 20),
            int(C_SEA[2] - warm_f * 60),
        )
        for gx in range(terr.grid_w):
            for gy in range(terr.grid_h):
                rx, ry = int(gx * cw), int(gy * ch)
                color  = C_ICE if terr.ice[gx][gy] else sea_col
                pygame.draw.rect(screen, color,
                                 (rx, ry, int(cw) + 1, int(ch) + 1))

        # ── 빙하 붕괴 표시 ────────────────────────────────────────────────
        if sim.last_collapse:
            cx, cy, r, t0 = sim.last_collapse
            if sim.turn - t0 < 12:
                pygame.draw.circle(screen, (255, 220, 120),
                                   (sx(cx), sy(cy)), int(r * SCALE), 2)

        # ── 사체 ──────────────────────────────────────────────────────────
        for c in sim.carcasses:
            cx_px, cy_px = sx(c.x), sy(c.y)
            # X 표시
            pygame.draw.line(screen, (180, 60, 60), (cx_px-3, cy_px-3), (cx_px+3, cy_px+3), 2)
            pygame.draw.line(screen, (180, 60, 60), (cx_px+3, cy_px-3), (cx_px-3, cy_px+3), 2)
        
        # ── 동물 그리기 (y 정렬: 뒤→앞) ──────────────────────────────────
        for a in sorted(sim.animals, key=lambda o: o.y):
            if not a.is_alive:
                continue

            r  = SPECIES_R[a.SPECIES]
            px = sx(a.x)
            py = sy(a.y)

            sprite_data = ANIMAL_SPRITES.get(a.SPECIES)

            if sprite_data:
                # 방향에 따라 이미지 선택 (살아있으므로 dead 분기 불필요)
                img  = sprite_data["right"] if a.facing >= 0 else sprite_data["left"]
                rect = img.get_rect(center=(px, py))
                screen.blit(img, rect)
            else:
                # 이미지 로드 실패 시 도형 fallback
                col = SPECIES_COLOR[a.SPECIES]
                pygame.draw.circle(screen, col, (px, py), r)
                if a.hunger > 80:
                    pygame.draw.circle(screen, C_RED, (px, py), r, 1)

            

            # 범고래 음파 링
            if a.SPECIES == "Orca":
                ring_timer = getattr(a, "echo_ring", 0)
                if ring_timer > 0:
                    ring_radius = int((20-ring_timer)* 4)
                    pygame.draw.circle(screen, (150, 220, 255),
                                       (px, py), ring_radius, 1)
                    a.echo_ring -=5 
        # ─────────────────────────────────────────────────────────────────────
        # [이펙트 기능] 사냥 / 번식 시각 효과 업데이트 및 그리기
        # ─────────────────────────────────────────────────────────────────────
        import time
        import math

        # main.py의 Simulation 객체에 쌓인 최신 효과들을 viz의 로컬 리스트로 가져옴
        if hasattr(sim, 'visual_effects'):
            while sim.visual_effects:
                eff_type, ex, ey = sim.visual_effects.pop(0)
                local_effects.append({
                    'type': eff_type,
                    'sx': ex * SCALE,
                    'sy': ey * SCALE,
                    'start_time': time.time()
                })

        now = time.time()
        remaining_effects = []

        for eff in local_effects:
            dt = now - eff['start_time']
            if dt > 0.6: continue  # 0.6초 동안만 임팩트 연출 후 소멸
            
            progress = dt / 0.6
            if eff['type'] == 'hunt':
                # 사냥 성공: 사방으로 확장하며 소멸하는 붉은색 파티클 효과
                for i in range(6):
                    ang = i * (2 * math.pi / 6)
                    dist = progress * 20
                    px = eff['sx'] + math.cos(ang) * dist
                    py = eff['sy'] + math.sin(ang) * dist
                    pygame.draw.circle(screen, C_RED, (int(px), int(py)), max(1, int(4 * (1 - progress))))
                    
            elif eff['type'] == 'reproduction':
                # 번식 성공: 분홍색 하트 효과가 위로 동동 떠오름 (f_sm 폰트 재활용)
                up_y = eff['sy'] - (progress * 25)
                try:
                    heart_surf = f_sm.render("♥", True, (255, 130, 190))
                    screen.blit(heart_surf, (int(eff['sx']) - 5, int(up_y) - 5))
                except:
                    pygame.draw.circle(screen, (255, 130, 190), (int(eff['sx']), int(up_y)), 5)

            remaining_effects.append(eff)
        local_effects = remaining_effects


        # ─────────────────────────────────────────────────────────────────────
        # [상태창 기능] 클릭한 동물 정보창 띄우기 (화면 좌측 상단 배치)
        # ─────────────────────────────────────────────────────────────────────
        if selected_animal and getattr(selected_animal, 'is_alive', True):
            # 선택된 동물의 발밑에 초록색 타겟 링 표시
            pygame.draw.circle(screen, C_GREEN, (int(selected_animal.x * SCALE), int(selected_animal.y * SCALE)), 12, 1)
            
            # 미니 정보창 박스 (반투명 어두운 배경 + 하늘색 테두리)
            bx, by, bw, bh = 15, 15, 185, 150
            info_surf = pygame.Surface((bw, bh))
            info_surf.set_alpha(200)
            info_surf.fill((22, 26, 36))
            screen.blit(info_surf, (bx, by))
            pygame.draw.rect(screen, C_TITLE, (bx, by, bw, bh), 1)
            
            # 프라이빗 변수(__hp, __hunger) 접근을 유연하게 처리하기 위한 헬퍼
            get_hp = lambda a: getattr(a, '_Animal__hp', getattr(a, 'hp', 100))
            get_hunger = lambda a: getattr(a, '_Animal__hunger', getattr(a, 'hunger', 0))
            
            status_lines = [
                f" 종 류 : {getattr(selected_animal, 'SPECIES', type(selected_animal).__name__)}",
                f" 성 별 : {'수컷(M)' if getattr(selected_animal, 'gender', 'M') == 'M' else '암컷(F)'}",
                f" 나 이 : {getattr(selected_animal, 'age', 0)} / {getattr(selected_animal, 'max_age', 100)}",
                f" 체 력 : {int(get_hp(selected_animal))}",
                f" 허 기 : {int(get_hunger(selected_animal))}",
                f" 행동 상태 : {getattr(selected_animal, 'state', 'idle')}"
            ]
            
            text_y = by + 12
            for line in status_lines:
                color = C_TEXT
                if "체력" in line and get_hp(selected_animal) < 30: color = C_RED
                screen.blit(f_sm.render(line, True, color), (bx + 12, text_y))
                text_y += 23
        # ─────────────────────────────────────────────────────────────────────
        # ── UI 패널 ───────────────────────────────────────────────────────
        pygame.draw.rect(screen, C_PANEL, (sw, 0, UI_W, sh))
        x0 = sw + 18

        screen.blit(f_bg.render("극지방 생태계", True, C_TITLE), (x0, 16))
        screen.blit(f_sm.render(f"턴: {sim.turn}", True, C_TEXT),  (x0, 52))
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
            mx = 90
            bw = int(min(1.0, c[sp] / 80) * mx)
            pygame.draw.rect(screen, (60, 70, 88), (x0 + 180, y + 3, mx, 9))
            pygame.draw.rect(screen, co,           (x0 + 180, y + 3, bw, 9))
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

        y = sh - 92
        for k, v in [("ESC", "종료"), ("Space", "일시정지"),
                     ("F", "4배속"), ("M", "온난화 +3 (가속)")]:
            screen.blit(f_sm.render(k, True, (250, 220, 120)), (x0, y))
            screen.blit(f_sm.render(v, True, C_TEXT),           (x0 + 70, y))
            y += 20

        # ── 종료 오버레이 ─────────────────────────────────────────────────
        if not sim.running:
            ov = pygame.Surface((sw + UI_W, sh), pygame.SRCALPHA)
            ov.fill((20, 0, 0, 180))
            screen.blit(ov, (0, 0))
            t  = f_bg.render("시뮬레이션 종료", True, (255, 210, 210))
            t2 = f_md.render((sim.end_reason or "종료")[:34],
                             True, (255, 190, 190))
            screen.blit(t,  ((sw + UI_W) // 2 - t.get_width()  // 2, sh // 2 - 40))
            screen.blit(t2, ((sw + UI_W) // 2 - t2.get_width() // 2, sh // 2))

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
