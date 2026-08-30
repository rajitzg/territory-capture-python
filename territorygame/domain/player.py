"""A match participant: identity, moving agent, and configured starting territory."""

from territorygame.api.grid_position import GridPosition
from territorygame.domain.agent import Agent
from territorygame.domain.player_id import PlayerId


class Player:
    def __init__(self, player_id: PlayerId, agent: Agent, starting_territory: list[GridPosition]) -> None:
        self._id = player_id
        self._agent = agent
        self._starting_territory = list(starting_territory)

    def get_id(self) -> PlayerId:
        return self._id

    def get_agent(self) -> Agent:
        return self._agent

    def get_starting_territory(self) -> list[GridPosition]:
        return list(self._starting_territory)
