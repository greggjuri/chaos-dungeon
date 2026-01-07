#!/usr/bin/env python3
"""CDK app entry point for Chaos Dungeon."""
import os

import aws_cdk as cdk

from stacks.api_stack import ChaosApiStack
from stacks.base_stack import ChaosBaseStack
from stacks.hosting_stack import ChaosHostingStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

environment = app.node.try_get_context("environment") or "dev"

# Certificate ARN for wildcard cert (required for hosting stack)
certificate_arn = app.node.try_get_context("certificateArn")

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

# Only create hosting stack for prod (or when explicitly enabled)
if environment == "prod" or os.environ.get("ENABLE_HOSTING") == "true":
    if not certificate_arn:
        raise ValueError(
            "certificateArn context is required for hosting stack. "
            "Use: cdk deploy -c certificateArn=arn:aws:acm:..."
        )

    hosting_stack = ChaosHostingStack(
        app,
        f"ChaosHosting-{environment}",
        api_stack=api_stack,
        environment=environment,
        certificate_arn=certificate_arn,
        env=env,
    )

app.synth()
