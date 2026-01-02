# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_task_notification_mode.py
from autobyteus.agent_team.task_notification.task_notification_mode import (
    ENV_TASK_NOTIFICATION_MODE,
    TaskNotificationMode,
    resolve_task_notification_mode,
)


def test_resolve_default_when_env_unset(monkeypatch):
    monkeypatch.delenv(ENV_TASK_NOTIFICATION_MODE, raising=False)
    assert resolve_task_notification_mode() == TaskNotificationMode.AGENT_MANUAL_NOTIFICATION


def test_resolve_env_value(monkeypatch):
    monkeypatch.setenv(ENV_TASK_NOTIFICATION_MODE, "system_event_driven")
    assert resolve_task_notification_mode() == TaskNotificationMode.SYSTEM_EVENT_DRIVEN


def test_resolve_env_value_case_insensitive(monkeypatch):
    monkeypatch.setenv(ENV_TASK_NOTIFICATION_MODE, "SYSTEM_EVENT_DRIVEN")
    assert resolve_task_notification_mode() == TaskNotificationMode.SYSTEM_EVENT_DRIVEN


def test_resolve_invalid_env_fallback(monkeypatch):
    monkeypatch.setenv(ENV_TASK_NOTIFICATION_MODE, "not-a-mode")
    assert resolve_task_notification_mode() == TaskNotificationMode.AGENT_MANUAL_NOTIFICATION
