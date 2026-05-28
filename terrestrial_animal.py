"""
육지동물 클래스

상속 관계:
    Animal (animal.py) → TerrestrialAnimal
"""

import math
import random
from animal import Animal


class TerrestrialAnimal(Animal):
    """
    육지에서 활동하는 동물의 클래스
    
    Animal을 상속받아 육지 활동에 필요한 속성과 메서드를 추가한다.
    
    공통 특성:
        - 활동 영역(territory)을 가지고 그 안에서 움직임
        - 집(home) 좌표를 중심으로 배회
        - 포식자로부터 도망갈 수 있음
        - 목표를 향해 이동할 수 있음
    """

    def __init__(self, name, hp, age, max_age, speed, hunger,
                 x, y, cold_resistance, gender,
                 gestation, prey_types, hunting_range,
                 attack, defense,
                 territory_range=150.0,
                 home_x=None, home_y=None):
        """
        육지동물 초기화
        
        Args:
            name, hp, age, max_age, speed, hunger, x, y, 
            cold_resistance, gender, attack, defense,
            reproduce_cool_max, gestation, prey_types, hunting_range:
                Animal 공통 속성 (부모 클래스로 전달)
            
            territory_range (float): 활동 가능 범위 반경 (픽셀)
            home_x, home_y (float or None): 집/영역의 중심 좌표
                None이면 초기 위치를 home으로 설정
        """
        # 부모 클래스(Animal)의 __init__ 호출
        # 객체지향의 상속을 활용해 공통 속성을 부모에게 위임한다
        super().__init__(
            name=name, hp=hp, age=age, max_age=max_age,
            speed=speed, hunger=hunger, x=x, y=y,
            cold_resistance=cold_resistance, gender=gender,
            gestation=gestation, prey_types=prey_types,
            hunting_range=hunting_range,
            attack=attack, defense=defense,
        )
        
        # TerrestrialAnimal 고유 속성
        self.territory_range = territory_range
        
        # 집 좌표: None이면 초기 위치를 home으로 설정
        # 동물이 태어난 곳을 자신의 영역 중심으로 인식
        self.home_x = home_x if home_x is not None else x
        self.home_y = home_y if home_y is not None else y
        
        # 도망 상태 추적 (flee_from에서 사용)
        self._is_fleeing = False
        self._flee_target = None   # 누구한테서 도망가는 중인지

    # 이동 관련 메서드
    
    def random_walk(self, world_w, world_h):
        """
        home 주변을 무작위로 배회
        
        동작:
            1. home에서 territory_range 안의 무작위 방향으로 이동
            2. 이미 territory 밖에 있다면 home 쪽으로 끌어당김
            3. 월드 경계도 함께 체크
        
        Args:
            world_w (float): 월드 가로 크기 — System이 넘겨준다
            world_h (float): 월드 세로 크기 — System이 넘겨준다
        
        Note:
            매 턴 호출하면 동물이 자연스럽게 움직이는 효과
            너무 자주 방향 바꾸지 않도록 일정 확률로만 새 방향 결정
            월드 크기는 System이 단일 출처로 관리하므로 기본값을 두지 않고 반드시 인자로 받음 (값 어긋남 방지)
        """
        if not self.is_alive:
            return
        
        # 현재 home까지의 거리 계산
        dist_from_home = self._distance_to_home()
        
        # territory 밖에 있으면 home 쪽으로 끌어당기는 힘 적용
        if dist_from_home > self.territory_range:
            # 60% 확률로 home 쪽으로 (자유도를 위해 100%는 아님)
            if random.random() < 0.6:
                self.move_toward(self.home_x, self.home_y, world_w, world_h)
                return
        
        # 일정 확률로만 새 방향 결정 (너무 자주 방향 바꾸면 부자연스러움)
        # 80%는 가만히, 20%만 새 방향
        if random.random() < 0.2:
            angle = random.uniform(0, 2 * math.pi)
            # speed의 50%로 천천히 배회 (도망/추격이 아니므로)
            move_dist = self.speed * 0.5
            new_x = self.x + math.cos(angle) * move_dist
            new_y = self.y + math.sin(angle) * move_dist
            
            # 월드 경계 처리
            self.x = max(0, min(world_w - 1, new_x))
            self.y = max(0, min(world_h - 1, new_y))
    
    def move_toward(self, target_x, target_y, world_w, world_h):
        """
        지정한 좌표로 speed만큼 이동
        
        동작:
            1. 목표까지의 방향 벡터 계산
            2. 정규화 후 speed만큼 이동
            3. 월드 경계 체크
        
        Args:
            target_x, target_y (float): 목표 좌표
            world_w, world_h (float): 월드 크기 — System이 넘겨준다
        
        Returns:
            float: 이동 후 목표까지 남은 거리
        
        Note:
            move_toward는 사냥, 무리 따라가기, 집으로 돌아가기 등 여러 상황에서 재사용
        """
        if not self.is_alive:
            return 0.0
        
        # 목표까지의 거리와 방향 계산
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        
        # 너무 가까우면 더 이상 이동하지 않음 (덜덜 떨림 방지)
        if distance < 1.0:
            return distance
        
        # 정규화된 방향 벡터 × speed
        move_x = (dx / distance) * self.speed
        move_y = (dy / distance) * self.speed
        
        # 위치 업데이트
        new_x = self.x + move_x
        new_y = self.y + move_y
        
        # 월드 경계 처리
        self.x = max(0, min(world_w - 1, new_x))
        self.y = max(0, min(world_h - 1, new_y))
        
        # 이동 후 남은 거리 반환 (사냥 거리 체크 등에 활용)
        return math.hypot(target_x - self.x, target_y - self.y)
    
    def flee_from(self, predator, world_w, world_h):
        """
        포식자로부터 반대 방향으로 도망
        
        동작:
            1. 포식자와의 방향 벡터 계산
            2. 반대 방향으로 이동 (속도는 평소보다 빠르게)
            3. 월드 경계 처리
        
        Args:
            predator (Animal): 도망갈 대상 (포식자)
            world_w, world_h (float): 월드 크기 — System이 넘겨줌
        
        Returns:
            bool: 도망 동작 수행 여부
        
        Note:
            도망 속도는 평소 speed의 1.3배
            공포 상황에서 더 빨라짐 표현
            도망 중에는 _is_fleeing 플래그가 True
        """
        if not self.is_alive or predator is None or not predator.is_alive:
            self._is_fleeing = False
            self._flee_target = None
            return False
        
        # 포식자로부터의 방향 벡터 (반대 방향이 도망 방향)
        dx = self.x - predator.x
        dy = self.y - predator.y
        distance = math.hypot(dx, dy)
        
        # 이미 같은 위치라면 무작위 방향으로
        if distance < 1e-6:
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            distance = 1.0
        
        # 도망 속도는 평소의 1.3배 (공포로 인한 가속)
        flee_speed = self.speed * 1.3
        
        # 정규화된 도망 방향 * 도망 속도
        move_x = (dx / distance) * flee_speed
        move_y = (dy / distance) * flee_speed
        
        # 위치 업데이트
        new_x = self.x + move_x
        new_y = self.y + move_y
        
        # 월드 경계 처리
        self.x = max(0, min(world_w - 1, new_x))
        self.y = max(0, min(world_h - 1, new_y))
        
        # 도망 상태 기록
        self._is_fleeing = True
        self._flee_target = predator
        
        return True
    
    # 헬퍼 메서드 (내부용)
    
    def _distance_to_home(self):
        """
        현재 위치에서 home까지의 거리를 반환
        
        Returns:
            float: home까지의 유클리드 거리
        """
        return math.hypot(self.x - self.home_x, self.y - self.home_y)
    
    def is_in_territory(self, x=None, y=None):
        """
        주어진 좌표 (또는 현재 위치)가 territory 안인지 확인
        
        Args:
            x, y (float or None): 확인할 좌표 (None이면 현재 위치)
        
        Returns:
            bool: territory 안이면 True
        
        Note:
            자식 클래스에서 활동 범위 판단에 활용할 수 있도록 제공
        """
        check_x = x if x is not None else self.x
        check_y = y if y is not None else self.y
        dist = math.hypot(check_x - self.home_x, check_y - self.home_y)
        return dist <= self.territory_range
    
    # 오버라이딩 메서드
    
    def update(self):
        """
        매 턴 호출되는 업데이트 메서드
        
        동작:
            1. 부모(Animal)의 update() 호출
               (배고픔 증가, 나이 증가, 쿨타임 감소)
            2. 도망 상태 자동 해제
               (포식자가 너무 멀어졌거나 죽었으면 도망 끝)
        
        Note:
            자식 클래스(PolarBear 등)는 이 메서드를 다시 오버라이딩해서 자신만의 update 로직을 추가할 수 있음 (다형성)
        """
        # 부모 클래스의 update 먼저 호출 - 객체지향의 상속 활용
        super().update()
        
        # 도망 상태 자동 해제 체크
        if self._is_fleeing and self._flee_target is not None:
            # 포식자가 죽었거나 너무 멀어졌으면 도망 끝
            if not self._flee_target.is_alive:
                self._is_fleeing = False
                self._flee_target = None
            else:
                dist = self.get_distance(self._flee_target)
                # 사냥 거리의 2배 이상 멀어졌으면 안전하다고 판단
                safe_distance = max(100.0, self._flee_target.hunting_range * 2)
                if dist > safe_distance:
                    self._is_fleeing = False
                    self._flee_target = None
    
    def __repr__(self):
        """
        디버깅용 문자열 표현
        
        Returns:
            str: 동물의 현재 상태를 요약한 문자열
        """
        status = "alive" if self.is_alive else "dead"
        fleeing = " [FLEEING]" if self._is_fleeing else ""
        return (f"<{type(self).__name__} {self.name} "
                f"pos=({self.x:.0f},{self.y:.0f}) "
                f"hp={self.hp:.0f} hunger={self.hunger:.0f} "
                f"{status}{fleeing}>")
