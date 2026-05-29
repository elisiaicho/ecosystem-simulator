import random
 
class System:
    """
    매 턴 모든 객체의 update()를 호출하는 관리자 클래스
    - 동물 등록/제거
    - 출산 객체 자동 수거 및 등록
    - 번식 시도 (매 턴 가까운 동종 탐색) --> Animal 클래스의 번식 매커니즘과 연결
    - 사냥 시도 (매 턴 가까운 먹잇감 탐색)  ---> Animal 클래스의 hunt 매서드와 연결
    - 종료 조건 감지
    """
 
    def __init__(self):
        self.objects    = []   # 등록된 모든 객체 (Animal 자손 + Krill + Event)
        self.turn       = 0
        self.game_over  = False
 
    
    # 등록 / 제거
    
 
    def add(self, object):
        """객체 등록 — Animal이면 _system 참조 주입"""
        object._system = self          # give_birth()에서 직접 add() 호출 가능
        self.objects.append(object)
 
    def remove(self, object):
        if object in self.objects:
            self.objects.remove(object)
 
    
    # 동물 목록 조회 게터 
    
 
    def get_alive_animals(self):
        """is_alive 속성이 있고 살아있는 객체만 반환"""
        return [o for o in self.objects
                if getattr(o, 'is_alive', False)]
 
    def get_events(self):
        """Event 자손 객체만 반환"""
        # Event 클래스를 import 안 해도 되도록 이름으로 체크
        return [o for o in self.objects
                if type(o).__mro__[-2].__name__ == 'Event'
                or hasattr(o, 'trigger')]
 
    
    # 사냥 처리
    
 
    def _process_hunting(self, animals):
        """
        prey_types가 있는 동물마다 가장 가까운 먹잇감을 찾아 hunt() 호출
        Krill은 eat_krill()로 별도 처리
        """
        for hunter in animals:
            if not getattr(hunter, 'is_alive', False):
                continue
            if not getattr(hunter, 'prey_types', []):
                continue
 
            # Krill 섭취 따로 처리
            krill_targets = [
                o for o in self.objects
                if type(o).__name__ == 'Krill' and getattr(o, 'is_alive', True)
                and hunter.get_distance(o) <= getattr(hunter, 'hunting_range', 0)
            ]
            if krill_targets and hasattr(hunter, 'eat_krill'):
                nearest_krill = min(krill_targets, key=lambda k: hunter.get_distance(k))
                hunter.eat_krill(nearest_krill)
                continue   # krill 먹었으면 이 턴 사냥 끝
 
            # 일반 동물 사냥
            prey = hunter.find_nearest(animals, hunter.prey_types)
            if prey:
                hunter.hunt(prey)
 
    
    # 번식 처리
    
 
    def _process_reproduction(self, animals):
        """
        can_reproduce()가 True인 동물끼리 가까우면 try_reproduce() 호출
        이미 번식한 쌍은 같은 턴에 중복 시도 안 함
        """
        reproduced = set()   # 이미 번식한 객체 id 추적
 
        for a in animals:
            if id(a) in reproduced:
                continue
            if not getattr(a, 'is_alive', False):
                continue
            if not hasattr(a, 'can_reproduce') or not a.can_reproduce():
                continue
 
            # 같은 종, 다른 성별, 가까운 파트너 탐색
            partners = [
                b for b in animals
                if b is not a
                and type(b) == type(a)
                and getattr(b, 'is_alive', False)
                and id(b) not in reproduced
                and hasattr(b, 'can_reproduce') and b.can_reproduce()
                and a.get_distance(b) <= getattr(a, 'hunting_range', 5)
            ]
            if not partners:
                continue
 
            partner = min(partners, key=lambda b: a.get_distance(b))
            baby = a.try_reproduce(partner)
 
            # try_reproduce가 새끼 객체를 반환하면 등록
            if baby is not None:
                self.add(baby)
                print(f"[System] 새끼 {baby.name} 등록됨 (턴 {self.turn})")
 
            reproduced.add(id(a))
            reproduced.add(id(partner))
 
    
    # 출산 처리
   
 
    def _process_births(self, animals):
        """
        임신 중이고 gestation <= 0인 동물의 give_birth() 호출
        give_birth()가 객체를 반환하면 등록 (give_birth 내부에서 _system.add() 안 할 경우 대비)
        """
        for animal in animals:
            if not getattr(animal, 'is_alive', False):
                continue
            if not getattr(animal, 'is_pregnant', False):
                continue
            if getattr(animal, 'gestation', 1) <= 0:
                baby = animal.give_birth()
                if baby is not None and baby not in self.objects:
                    self.add(baby)
                    print(f"[System] 출산: {baby.name} 등록됨 (턴 {self.turn})")
 
    
    # 이동 처리
    
 
    def _process_movement(self, animals):
        """
        먹잇감이 없으면 random_walk / random_swim
        먹잇감이 있으면 move_toward (hunt()에서 처리되므로 여기선 배회만)
        """
        for animal in animals:
            if not getattr(animal, 'is_alive', False):
                continue
            # 이미 hunt()에서 이동했을 동물은 skip — 간단히 prey_types 없는 동물만 이동
            if getattr(animal, 'prey_types', []):
                continue
            if hasattr(animal, 'random_walk'):
                animal.random_walk()
            elif hasattr(animal, 'random_swim'):
                animal.random_swim()
 
    
    # 종료 조건 체크
    
 
    def _check_game_over(self):
        """
        1) event_end.active == True (운석 충돌)
        2) ESC 키 입력 — pygame 환경이면 외부에서 game_over = True 설정
        3) 동물이 모두 멸종
        """
        # event_end 감지
        for obj in self.objects:
            if type(obj).__name__ == 'event_end' and getattr(obj, 'active', False):
                print("[System] 운석 충돌 — 게임 종료")
                self.game_over = True
                return
 
        # 전멸 감지
        alive = self.get_alive_animals()
        if len(alive) == 0:
            print("[System] 모든 동물이 멸종했습니다 — 게임 종료")
            self.game_over = True
 
    
    # 메인 update
    
 
    def update(self):
        """
        매 턴 호출 순서:
        1. 이벤트 update (온도 변화, 눈보라 등)
        2. 동물 개별 update (hunger++, age++, gestation--, ...)
        3. 출산 처리
        4. 사냥 처리
        5. 번식 처리
        6. 이동 처리 (prey 없는 동물 배회)
        7. 죽은 객체 제거
        8. 종료 조건 체크
        """
        if self.game_over:
            return
 
        self.turn += 1
        print(f"\n===== 턴 {self.turn} =====")
 
        alive = self.get_alive_animals()
 
        # 1. 이벤트 먼저
        for obj in self.objects:
            if hasattr(obj, 'trigger'):          # Event 자손
                obj.update(alive)
 
        # 2. 동물 개별 update
        for obj in alive:
            if not hasattr(obj, 'trigger'):      # 이벤트 제외
                obj.update()
 
        # 3. 출산
        self._process_births(self.get_alive_animals())
 
        # 4. 사냥
        self._process_hunting(self.get_alive_animals())
 
        # 5. 번식
        self._process_reproduction(self.get_alive_animals())
 
        # 6. 이동
        self._process_movement(self.get_alive_animals())
 
        # 7. 죽은 객체 제거
        before = len(self.objects)
        self.objects = [
            o for o in self.objects
            if getattr(o, 'is_alive', True)      # is_alive 없는 객체(Event)는 유지
        ]
        removed = before - len(self.objects)
        if removed:
            print(f"[System] 이번 턴 {removed}마리 제거됨")
 
        # 8. 종료 체크
        self._check_game_over()
 
    
    # 디버그 출력
    
 
    def status(self):
        """현재 생존 객체 현황 출력"""
        print(f"\n--- 턴 {self.turn} 현황 ---")
        alive = self.get_alive_animals()
        from collections import Counter
        counts = Counter(type(o).__name__ for o in alive)
        for species, count in sorted(counts.items()):
            print(f"  {species}: {count}마리")
        print(f"  총 {len(alive)}마리 생존 중")
