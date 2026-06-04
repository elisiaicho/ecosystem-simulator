import pygame
import random
import time
import math

# --- 색상 및 설정 ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
PINK = (255, 182, 193)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

ANIMAL_RADIUS = 10 # 화면에 그려질 동물의 크기

class VisualManager:
    def __init__(self, screen, system):
        self.screen = screen
        self.system = system # 전체 동물 리스트를 가진 System 객체
        self.selected_animal = None # 현재 클릭해서 선택된 동물
        
        # 임시 시각 효과를 저장하는 리스트 (효과 내용, 좌표, 생성 시간, 지속 시간)
        self.effects = [] 

    # ==========================================
    # 기능 1: 동물 클릭 감지
    # ==========================================
    def handle_click(self, mouse_pos):
        """마우스 클릭 좌표를 받아 어떤 동물이 클릭되었는지 확인합니다."""
        self.selected_animal = None # 일단 선택 해제
        
        mx, my = mouse_pos
        for animal in self.system.animals:
            if not animal.is_alive: continue
            
            # 동물과 마우스 사이의 거리 계산 (피타고라스)
            dist = math.hypot(animal.x - mx, animal.y - my)
            
            # 동물의 반지름 안에 클릭했다면 선택!
            if dist <= ANIMAL_RADIUS + 5: # 약간의 클릭 판정 버프
                self.selected_animal = animal
                print(f"[GUI] {animal.name} 선택됨")
                return # 한 마리만 선택하고 종료

    # ==========================================
    # 기능 1: 상태창 그리기 (UI)
    # ==========================================
    def draw_status_window(self):
        """선택된 동물이 있다면 화면 우측 상단에 상태창을 그립니다."""
        if not self.selected_animal or not self.selected_animal.is_alive:
            return

        a = self.selected_animal
        
        # 창 설정
        win_w, win_h = 250, 300
        win_x, win_y = self.screen.get_width() - win_w - 10, 10
        
        # 배경 (반투명 블랙)
        s = pygame.Surface((win_w, win_h))
        s.set_alpha(200) # 투명도
        s.fill(BLACK)
        self.screen.blit(s, (win_x, win_y))
        
        # 테두리
        pygame.draw.rect(self.screen, WHITE, (win_x, win_y, win_w, win_h), 2)

        # 텍스트 그리기 (폰트 객체는 외부에서 초기화해서 들고오는 게 좋습니다)
        font = pygame.font.SysFont("malgungothic", 16) # 한글 폰트 (윈도우 기준)
        
        status_text = [
            f"[{a.name}]",
            f"-------------------",
            f"성별: {'수컷' if a.gender == 'M' else '암컷'}",
            f"나이: {a.age} / {a.max_age}",
            f"체력(HP): {int(a.hp)} / 100",
            f"배고픔: {int(a.hunger)} / 200",
            f"속도: {a.speed}",
            f"-------------------",
            f"상태: {'임신 중' if a.is_pregnant else '일반'}",
            f"번식 쿨타임: {a.reproduce_cool}턴"
        ]

        # 체력바 그리기 예시
        hp_bar_w = 150
        hp_bar_x, hp_bar_y = win_x + 80, win_y + 112
        pygame.draw.rect(self.screen, (50, 50, 50), (hp_bar_x, hp_bar_y, hp_bar_w, 15)) # 배경
        pygame.draw.rect(self.screen, RED, (hp_bar_x, hp_bar_y, hp_bar_w * (a.hp/100), 15)) # 현재 HP

        # 텍스트 blit
        for i, text in enumerate(status_text):
            color = WHITE
            if "체력" in text: color = RED
            elif "배고픔" in text and a.hunger > 100: color = PINK
            elif "임신" in text: color = GREEN
            
            txt_surf = font.render(text, True, color)
            self.screen.blit(txt_surf, (win_x + 15, win_y + 15 + (i * 22)))


    # ==========================================
    # 기능 2, 3: 시각 효과 등록
    # ==========================================
    def add_effect(self, type, x, y, duration=1.0):
        """사냥/번식 성공 시 시스템(서버)이 이 메서드를 호출하여 효과를 등록합니다."""
        self.effects.append({
            'type': type,
            'x': x,
            'y': y,
            'start_time': time.time(),
            'duration': duration,
            'particles': [] # 필요시 파티클 좌표 저장용
        })
        
        # 사냥 효과일 경우 주변에 붉은 파티클 초기화
        if type == 'predation':
            for _ in range(10):
                self.effects[-1]['particles'].append([
                    random.uniform(-15, 15), # dx
                    random.uniform(-15, 15), # dy
                    random.uniform(2, 5)     # speed
                ])

    # ==========================================
    # 메인 Render 루프 (매 프레임 호출)
    # ==========================================
    def render(self):
        # 1. 모든 동물 그리기 (간단히 원으로 표시)
        for animal in self.system.animals:
            if not animal.is_alive: continue
            
            # 성별에 따른 색상 구분
            color = BLUE if animal.gender == 'M' else PINK
            
            # 선택된 동물은 테두리 강조
            if animal is self.selected_animal:
                pygame.draw.circle(self.screen, GREEN, (int(animal.x), int(animal.y)), ANIMAL_RADIUS + 3, 3)

            pygame.draw.circle(self.screen, color, (int(animal.x), int(animal.y)), ANIMAL_RADIUS)
            
            # 임신한 경우 위에 작은 초록불 표시
            if animal.is_pregnant:
                pygame.draw.circle(self.screen, GREEN, (int(animal.x), int(animal.y) - 15), 4)

        # 2. 시각 효과 그리기 및 관리
        current_time = time.time()
        new_effects = []
        for effect in self.effects:
            # 지속 시간이 지났으면 삭제
            if current_time - effect['start_time'] > effect['duration']:
                continue
            
            # 기능 3: 번식 성공 시 (하트 이모지 그리기)
            if effect['type'] == 'reproduction':
                # 간단히 분홍색 하트 원으로 대체 (실제로는 하트 이미지를 로드해서 blit 해야 합니다)
                # 하트가 서서히 위로 올라가는 연출
                alpha = 255 * (1 - (current_time - effect['start_time']) / effect['duration']) # 투명도 애니메이션
                offset_y = 30 * (current_time - effect['start_time']) / effect['duration'] # 위로 이동
                
                s = pygame.Surface((30, 30))
                s.set_colorkey(BLACK)
                s.set_alpha(int(alpha))
                
                # 하트 이모지 블릿 (폰트 필요)
                heart_font = pygame.font.SysFont("seguiemj", 25) # 윈도우 이모지 폰트
                txt = heart_font.render("❤️", True, WHITE) # 색상은 폰트가 결정함
                s.blit(txt, (0,0))
                
                self.screen.blit(s, (effect['x'] - 10, effect['y'] - 20 - offset_y))

            # 기능 2: 사냥 성공 시 (붉은 파티클 터짐)
            elif effect['type'] == 'predation':
                for p in effect['particles']:
                    px = effect['x'] + p[0]
                    py = effect['y'] + p[1]
                    size = max(1, int(3 * (1 - (current_time - effect['start_time']) / effect['duration'])))
                    pygame.draw.circle(self.screen, RED, (int(px), int(py)), size)
                    # 파티클 확산 이동
                    p[0] *= 1.05 
                    p[1] *= 1.05

            new_effects.append(effect)
            
        self.effects = new_effects # 살아남은 효과들만 갱신

        # 3. 상태창 그리기
        self.draw_status_window()