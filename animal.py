import math
import random



# 공통 부모 animal 만들기 
class Animal:
    def __init__(self, name, hp, age, max_age, speed, hunger, x, y, 
                 cold_resistance, gender, gestation, prey_types, hunting_range,
                 attack, defense):

        # 공통 속성 
        self.name            = name          # penguin, seal, polarbear, articfox, orca, articcod, krill, reindeer
        self.hp              = hp            #hp 범위 0 - 100 
        self.age             = age           # 현재 나이
        self.max_age         = max_age       # 수명 각 동물마다 다르게 설정할듯. random이용해서 난수 뽑아서 해야하지 않을까 자연사위해
        self.speed           = speed         # 0- 200 최대
        self.hunger          = hunger        # hunger 범위 0~100
        self.x               = x             # x좌표
        self.y               = y             # y좌표
        self.cold_resistance = cold_resistance   
        self.gender          = gender        # "M"(Male) or "F"(Female)
        self.is_alive        = True
        self.reproduce_cool  = 0             # 번식 쿨타임
        self.is_pregnant     = False
        self.gestation       = gestation
        self.prey_types      = prey_types
        self.hunting_range   = hunting_range
        self.attack          = attack
        self.defense         = defense
        self._system = None 

    # 공통 메서드 

    def eat(self, amount):
        self.hunger = max(0, self.hunger - amount)      # 몇몇 초식동물에 적용

    def take_damage(self, damage):                       #포식자와 피식자의 생태계 구현
        if not self.is_alive:
            return
        
        self.hp -= damage
        if self.hp <= 0:
            self.die()

    def die(self):                                      # 소멸자
        self.is_alive = False
        print(f"{self.name}이(가) 죽었다.")

    def get_distance(self, other):                                # 거리 구현으로, 공격 범위 구현 필요
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def update(self):                                            # 턴 호출
        """매 턴 호출해야함"""
        if not self.is_alive:
            return
        self.hunger += 4
        self.age +=1
        if self.age >= self.max_age:
            self.die()       #여기도 maxdage설정 필요
            return
        if self.reproduce_cool > 0:
            self.reproduce_cool -= 1
        if self.hunger >= 200:
            if self.is_alive:
                self.die()
        if self.is_pregnant:
            self. gestation -= 1
                #이미 system에서 출산을 구현함. 
                #여기도 자식클래스에서 출산 오버라이딩 해야됨(새끼 동물 객체 생성후, 동물 리스트에 추가)
        

    def can_reproduce(self):                                    # 번식 기능 1
        return (
            self.is_alive            and
            self.reproduce_cool == 0 and
            self.hunger < 60         and
            not self.is_pregnant
        )

    def try_reproduce(self, other):                            # 번식 기능 2
        """번식 시도 + 새끼 반환 (자식 클래스에서 오버라이드하셈)"""
        if type(self) != type(other):   return None
        if self.gender == other.gender: return None
        if not self.can_reproduce():    return None
        if not other.can_reproduce():   return None

        # 암컷(Female)을 찾아 임신시키기
        if self.gender == "Female":
            self.is_pregnant = True
            # 임신 기간 설정 (오버라이딩 필요)
        elif other.gender == "Female":
            other.is_pregnant = True
            #여기도 오버라이딩 필요함 (gestation은 종별로 설정)
        self.reproduce_cool  = 10
        other.reproduce_cool = 10
        print(f"{self.name}와 {other.name}이(가) 번식했다.")
        return NotImplementedError  # 자식 클래스에서 새끼 객체 반환해야함
    
    def give_birth(self):
        #gestation 고려, 그 시간 이후 새끼 객체를 반환해야함
        if self.is_pregnant and self.gestation <=0:
            self.is_pregnant = False
            self.reproduce_cool = 10
            print(f"{self.name}이/가 새끼를 낳았습니다.")
            return NotImplementedError   #여기도 자식에서 오버라이딩 해야됨
        
    
    def find_nearest(self, animals, target_types):
        investigating_animals = (
            animal for animal in animals 
            if type(animal).__name__ in target_types and animal.is_alive
        )
        
        return min(investigating_animals, key=self.get_distance, default=None)


    def hunt(self, target):
        distance = self.get_distance(target)
        hunt_prob = self.speed/ (self.speed + target.speed) * (1- 1/5 * (distance/ self.hunting_range))
        if distance <= self.hunting_range:
            if random.random() < hunt_prob:
                target.take_damage(self.attack)  #타겟에게 피해
            if not target.is_alive: 
                self.hunger = max(0,self.hunger -40)  #사냥 성공시 배고픔이 감소할 것
                print(f"{self.name}이(가) {target.name} 사냥에 성공했습니다. 확률 {hunt_prob:.0%}, 거리 {distance:.1f}/{self.hunting_range}")
        else:
            print(f"{target.name}이(가) 사냥 거리를 벗어났습니다.확률 {hunt_prob:.0%}, 거리 {distance:.1f}/{self.hunting_range}")
        
    # eatkrill 여기 넣는거는 객체 지향에서 깔 거 같아가지고 안넣음. 필히 marineanimal에서 넣어주셈.
