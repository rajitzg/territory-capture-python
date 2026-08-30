from territorygame.api.agent_controller import AgentController
from territorygame.controller.available_controllers import ALL


def test_all_lists_the_four_expected_options_in_order():
    assert [option.label for option in ALL] == [
        "Basic State Machine", "Enemy State Machine", "Random State Machine", "Candidate Controller",
    ]


def test_every_factory_produces_an_agent_controller_given_a_seed():
    for option in ALL:
        controller = option.factory(1001)
        assert isinstance(controller, AgentController)


def test_str_returns_the_label():
    assert str(ALL[0]) == "Basic State Machine"
