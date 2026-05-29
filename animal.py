import math
import random
import abc

HUNGER_INCREASE_RATE = 2
"""매 턴마다 배고픔이 증가하는 양"""
HP_DECREASE_RATE_FOR_HUNGER = 10
"""배고픔이 100 이상일 때 매 턴마다 hp가 감소하는 양"""
HUNGER_THRESHOLD = 100
"""배고픔에 의해 hp가 감소하기 시작하는 배고픔 수치"""
PREGNANT_CAPABLE_HUNGER= 60
"""번식 가능한 최대 허기량"""
REPRODUCE_COOLTIME = 10
"""번식 쿨타임. 몇턴 더 버텨야 하는지"""
# 공통 부모 animal 만들기 
class Animal(abc.ABC):
    def __init__(self, hp, age, max_age, speed, hunger, x, y, 
                 cold_resistance, gender, gestation, prey_types, hunting_range,
                 attack, defense):

        # 공통 속성 
                                # penguin, seal, polarbear, articfox, orca, articcod, krill, reindeer
        self.__hp              = hp            #hp 범위 0 - 100 
        self.age             = age           # 현재 나이
        self.max_age         = max_age       # 수명 각 동물마다 다르게 설정할듯. random이용해서 난수 뽑아서 해야하지 않을까 자연사위해
        self.speed           = speed         # 0- 200 최대
        self.__hunger          = hunger        # hunger 범위 0~100
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

    #게터
    @property
    def name(self):
        return type(self).__name__
    @property
    def hp(self):
        return self.__hp
    @property
    def hunger(self):
        return self.__hunger
    #세터

    @hp.setter
    def hp(self, value):
        self.__hp = max(0, min(100,value))  #hp 0-100 유지
        if self.__hp ==0:
            self.is_alive = False 
            print(f"{self.name}이(가) 죽었다")
    
    @hunger.setter
    def hunger(self, value):
        self.__hunger = max(0, min(200, value))   #허기 자동 조절 

        if self.__hunger >= 200 and self.is_alive:
            self.hp = 0


    # 공통 메서드 


    def eat(self, amount):
        self.hunger = max(0, self.hunger - amount)      # 몇몇 초식동물에 적용

    

    def get_distance(self, other):                                # 거리 구현으로, 공격 범위 구현 필요
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def update(self):                                            # 턴 호출
        """매 턴 호출해야함"""
        if not self.is_alive:
            return
        
        self.hunger += HUNGER_INCREASE_RATE
        self.age +=1
        
        if self.age >= self.max_age:
            self.hp = 0
            return
            
        if self.reproduce_cool > 0:
            self.reproduce_cool -= 1
        
        if self.hunger >= HUNGER_THRESHOLD:
            self.hp -= HP_DECREASE_RATE_FOR_HUNGER
        
        if self.is_pregnant:
            self.gestation -= 1
                #이미 system에서 출산을 구현함. 
                #여기도 자식클래스에서 출산 오버라이딩 해야됨(새끼 동물 객체 생성후, 동물 리스트에 추가)
        

    def can_reproduce(self):                                    # 번식 기능 1
        return (
            self.is_alive            and
            self.reproduce_cool == 0 and
            self.hunger < PREGNANT_CAPABLE_HUNGER         and
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
        self.reproduce_cool  = REPRODUCE_COOLTIME
        other.reproduce_cool = REPRODUCE_COOLTIME
        print(f"{self.name}와 {other.name}이(가) 번식했다.")
        return None                                             # 자식 클래스에서 새끼 객체 반환해야함
    
    def give_birth(self):
        #gestation 고려, 그 시간 이후 새끼 객체를 반환해야함
        if self.is_pregnant and self.gestation <=0:
            self.is_pregnant = False
            self.reproduce_cool = REPRODUCE_COOLTIME
            print(f"{self.name}이/가 새끼를 낳았습니다.")
            return None                                             #여기도 자식에서 오버라이딩 해야됨
        return None
    
    def find_nearest(self, animals, target_types):
        investigating_animals = (
            animal for animal in animals 
            if type(animal).__name__ in target_types and getattr(animal,'is_alive', False)
        )
        
        return min(investigating_animals, key=self.get_distance, default=None)


    def hunt(self, target):
        distance = self.get_distance(target)
        hunt_prob = self.speed/ (self.speed + target.speed) * (1- 1/5 * (distance/ self.hunting_range))
        if distance <= self.hunting_range:
            if random.random() < hunt_prob:
                target.hp -=self.attack  #타겟에게 피해
            else:
                print(f"{target.name}이/가 도망쳤습니다.") 

            if not target.is_alive: 
                self.hunger = max(0,self.hunger -self.attack *2)  #사냥 성공시 배고픔이 감소할 것 이떄 감소량은 attack에 비례
                print(f"{self.name}이(가) {target.name} 사냥에 성공했습니다. 확률 {hunt_prob:.0%}, 거리 {distance:.1f}/{self.hunting_range}")
            else:
                print(f"{self.name}이(가) {target.name} 피해를 입혔지만 사냥하진 못하였습니다.")
        else:
            print(f"{target.name}이(가) 사냥 거리를 벗어났습니다.확률 {hunt_prob:.0%}, 거리 {distance:.1f}/{self.hunting_range}")
        
    # eatkrill 여기 넣는거는 객체 지향에서 깔 거 같아가지고 안넣음. 필히 marineanimal에서 넣어주셈.
