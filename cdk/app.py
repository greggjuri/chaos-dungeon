#!/usr/bin/env python3
"""CDK app entry point for Chaos Dungeon."""
import os

import aws_cdk as cdk

from stacks.api_stack import ChaosApiStack
from stacks.base_stack import ChaosBaseStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

environment = app.node.try_get_context("environment") or "dev"

base_stack = ChaosBaseStack(
    app,
    f"ChaosBase-{environment}",
    environment=environment,
    env=env,
)

api_stack = ChaosApiStack(
    app,
    f"ChaosApi-{environment}",
    environment=environment,
    base_stack=base_stack,
    env=env,
)

app.synth()
