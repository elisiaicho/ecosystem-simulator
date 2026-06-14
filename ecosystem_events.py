"""
ecosystem_events.py
-------------------
담당: 1202 김산하

환경 이벤트. 생태계를 '한 방에' 무너뜨리지 않도록 강도를 완만하게 설계했다.
(이벤트가 너무 세면 그 자체로 연쇄 멸종을 유발하므로, 교란은 작게 두고
 종료 이벤트만 치명적으로 둔다 — 계획서 구조 유지)

- Blizzard            : 추위에 약한 개체(cold_resistance < 0.7)에 소량 피해
- GlacierCollapse     : 빙판 일부 구역에 소량 피해
- Starvation          : 크릴 바이오매스가 바닥일 때만 굶주림 추가
- AiBoilingApocalypse : 종료 이벤트(운석 대체). 확률·결과는 운석과 동일.
"""

import random
from abc import ABC, abstractmethod


class Event(ABC):
    name = "Event"

    @abstractmethod
    def trigger(self, sim):
        """시뮬레이션에 이벤트 효과를 적용하고 로그 문자열 리스트를 반환."""
        raise NotImplementedError

class Blizzard(Event):
    """눈보라 — 추위에 약한 개체에만 소량 피해."""
    name = "Blizzard"
    def trigger(self, sim):
        for a in sim.animals:
            if a.is_alive and a.cold_resistance < 0.7:
                a.take_damage((0.7 - a.cold_resistance) * 14)
        return ["[눈보라] 추위에 약한 동물이 약해졌습니다."]


class GlacierCollapse(Event):
    """빙하 붕괴 — 랜덤 얼음 구역에 소량 피해."""
    name = "GlacierCollapse"
    def trigger(self, sim):
        cells = getattr(sim.terrain, "ice_cells", None)
        if cells:
            cx, cy = random.choice(cells)
        else:
            cx = random.uniform(0, sim.world_w)
            cy = random.uniform(0, sim.world_h * 0.3)
        r = 6.0
        for a in sim.animals:
            if a.is_alive and (a.x - cx) ** 2 + (a.y - cy) ** 2 <= r * r:
                a.take_damage(18)
        sim.last_collapse = (cx, cy, r, sim.turn)
        return ["[빙하 붕괴] 일부 빙하 구역의 동물이 피해를 입었습니다."]


class Starvation(Event):
    """먹이 부족 — 크릴 바이오매스가 임계 이하일 때만 발동."""
    name = "Starvation"
    def trigger(self, sim):
        for a in sim.animals:
            if a.is_alive:
                a.hunger = min(100.0, a.hunger + 4)
        return ["[먹이 부족] 크릴이 부족해 모든 동물이 더 굶주립니다."]


class AiBoilingApocalypse(Event):
    """AI 무한질주로 인한 지구 온난화 — 바닷물 전량 증발, 전종 멸종(종료).

    원래 계획서의 '운석 충돌' 종료 이벤트를 대체. 확률·결과는 동일하게 유지.
    """
    name = "AiBoilingApocalypse"
    def trigger(self, sim):
        sim.running = False
        sim.end_reason = "AI 폭주 → 지구 온난화로 바닷물 전량 증발"
        for a in sim.animals:
            a.take_damage(99999)
        return [
            "[AI 무한질주]",
            "  AI 데이터센터의 폭주로 지구 온난화가 임계점을 돌파했습니다.",
            "  바닷물이 모두 증발하여 극지방 생태계 전체가 소멸했습니다.",
        ]
