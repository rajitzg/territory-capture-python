"""Registry of controller implementations the GUI offers per player slot."""

from dataclasses import dataclass
from typing import Callable

from candidate.candidate_controller import CandidateController
from candidate.examples.basic_state_machine import BasicStateMachine
from candidate.examples.random_state_machine import RandomStateMachine
from territorygame.api.agent_controller import AgentController
from territorygame.controller.enemy_state_machine import EnemyStateMachine


@dataclass(frozen=True)
class ControllerOption:
    """The factory takes the player slot's configured random seed
    (GameConfig.controller_seeds); most controllers have no randomness of
    their own and just ignore it."""

    label: str
    factory: Callable[[int], AgentController]

    def __str__(self) -> str:
        return self.label


ALL: list[ControllerOption] = [
    ControllerOption("Basic State Machine", lambda seed: BasicStateMachine()),
    ControllerOption("Enemy State Machine", EnemyStateMachine),
    ControllerOption("Random State Machine", lambda seed: RandomStateMachine()),
    ControllerOption("Candidate Controller", lambda seed: CandidateController()),
]
