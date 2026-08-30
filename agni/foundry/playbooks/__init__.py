"""Importing this package registers every shipped playbook."""

from agni.foundry.playbooks import agentic_infra, identity, social, support  # noqa: F401
from agni.foundry import sandbox as _sandbox  # noqa: F401
