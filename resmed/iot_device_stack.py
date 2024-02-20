from os import path
from aws_cdk import (
    # Duration,
    Stack,
    CfnOutput,
    Duration,
    # aws_sqs as sqs,
)

import aws_cdk.aws_s3 as s3

from constructs import Construct


class IotDeviceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(self, "IotDeviceStackBucket")



