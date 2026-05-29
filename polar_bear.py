
from animal import Animal
from terrestrial_animal import TerrestrialAnimal
import random

# polarbear 자식 클래스
class PolarBear(TerrestrialAnimal):
    def __init__(self, name, hp,age, max_age, speed, hunger, x, y, 
                 cold_resistance, gender, reproduce_cool=0, gestation=10, 
                 hunting_range = 30, attack = 50 , defense = 100, territory_range = 5.0):
        super().__init__( 
            name            = name,
            hp              = hp,
            age             = age,
            max_age         = max_age,
            speed           = speed,
            hunger          = hunger,
            x               = x,
            y               = y,
            cold_resistance = cold_resistance,
            gender          = gender,
            reproduce_cool  = reproduce_cool,
            gestation       = gestation,
            # Animal 공통 — 아래는 PolarBear 고정값
            prey_types      = ['ArcticCod', 'Penguin', 'Seal', 'Reindeer'],
            hunting_range   = hunting_range,
            attack          = attack,
            defense         = defense,
            # TerrestrialAnimal 전용
            territory_range = territory_range,
            home_x          = x,    # 처음 위치를 home으로 설정
            home_y          = y,
        ) 
             
        self.last_kill        = False           # articfox 구현 위해 넣어야 하는것  

        def hunt(self, target): 
            """Amnimal.hunt() 오버라이드, 사냥 성공시 lask_kill 구현하기"""
            success = super().hunt(target)
            if success:
                self.last_kill =True
            return success
        
        def give_birth(self):
            """가장 중요한 번식 시스템을 오버라이드함"""
            super().give_birth()
            baby = PolarBear(
                name            = f"{self.name}의 새끼",
                hp              = 100,
                age             = 0,
                max_age         = self.max_age,
                speed           = self.speed,
                hunger          = 0,
                x               = self.x,
                y               = self.y,
                cold_resistance = self.cold_resistance,
                gender          = random.choice(["Male", "Female"]),
            )
            return baby
        
        def roar(self):
            print(f"{self.name}이 포효했다")

        def hibernate_prepare(self):
            print(f'{self.name}이 동면에 들어간다. 이제 움직이지 않는다')

        def update(self):
            super.update()
            self.last_kill = False
