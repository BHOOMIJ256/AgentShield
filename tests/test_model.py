from agentshield import Action, Decision, Mode


def test_shadow_mode_lets_everything_through():
    for action in Action:
        assert Decision(action).enforced_action is Action.ALLOW


def test_enforce_mode_applies_the_decision():
    for action in Action:
        assert Decision(action, mode=Mode.ENFORCE).enforced_action is action
