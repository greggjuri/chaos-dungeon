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

# Only create hosting stack when certificateArn is provided
# For prod: cdk deploy ChaosHosting-prod -c environment=prod -c certificateArn=arn:aws:acm:...
# For dev:  ENABLE_HOSTING=true cdk deploy ChaosHosting-dev -c certificateArn=arn:aws:acm:...
should_create_hosting = (
    environment == "prod" or os.environ.get("ENABLE_HOSTING") == "true"
)

if should_create_hosting and certificate_arn:
    hosting_stack = ChaosHostingStack(
        app,
        f"ChaosHosting-{environment}",
        api_stack=api_stack,
        environment=environment,
        certificate_arn=certificate_arn,
        env=env,
    )
elif should_create_hosting:
    # Hosting eligible but no cert - print hint if user tries to deploy it
    print(
        f"Note: ChaosHosting-{environment} requires certificateArn context. "
        "Use: cdk deploy ChaosHosting-prod -c environment=prod "
        "-c certificateArn=arn:aws:acm:us-east-1:ACCOUNT:certificate/ID"
    )

app.synth()
