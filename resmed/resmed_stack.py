from os import path
from aws_cdk import (
    # Duration,
    Stack,
    CfnOutput,
    Duration,
    # aws_sqs as sqs,
)

import aws_cdk.aws_appsync as appsync
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda as lambda_
from aws_cdk import aws_iot as iot
from aws_cdk import aws_sns as sns
from aws_cdk import aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_kinesis as kinesis
from aws_cdk.aws_lambda_event_sources import KinesisEventSource, DynamoEventSource

from constructs import Construct


class ResmedStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        dirname = "./graphql-lambda"
        polar_dirname = "./polar-lambda"
        lambda_db_dirname = "./lambda_db"

        api = appsync.GraphqlApi(
            self,
            "Api",
            name="demo",
            schema=appsync.SchemaFile.from_asset(path.join(dirname, "schema.graphql")),
            authorization_config=appsync.AuthorizationConfig(
                default_authorization=appsync.AuthorizationMode(
                    authorization_type=appsync.AuthorizationType.API_KEY,
                )
            ),
            xray_enabled=True,
        )

        fn = lambda_.Function(
            self,
            "graphqlLambda",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="main.handler",
            code=lambda_.Code.from_asset(dirname),
            memory_size=1024,
        )

        lambdaSource = api.add_lambda_data_source("LambdaSource", fn)

        # Create Resolver
        lambdaSource.create_resolver(
            id="ListeNotes", type_name="Query", field_name="listNotes"
        )

        lambdaSource.create_resolver(
            id="createNote", type_name="Mutation", field_name="createNote"
        )

        lambdaSource.create_resolver(
            id="deleteNote", type_name="Mutation", field_name="deleteNote"
        )

        demo_table = dynamodb.Table(
            self,
            "DemoTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
        )
        users_table = dynamodb.Table(
            self,
            "UsersTable",
            partition_key=dynamodb.Attribute(
                name="username", type=dynamodb.AttributeType.STRING
            ),
        )
        demo_table.grant_full_access(fn)
        fn.add_environment("TableName", demo_table.table_name)

        # IOT THING
        topic_name = "topic/test"
        iot_thing = iot.CfnThing(
            self,
            "TestiotDevice",
            thing_name="TestiotDevice",
        )

        iot_role = iam.Role(
            self,
            "IotRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description="Iot Role for the iot ",
        )
        iot_cert_policy = iot.CfnPolicy(
            self,
            "IotCertPolicy",
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "iot:Connect",
                        ],
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:client/{iot_thing.thing_name}",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["iot:Publish"],
                        "Resource": f"arn:aws:iot:{self.region}:{self.account}:{topic_name}",
                    },
                ],
            },
            policy_name="iot_cert_policy",
        )

        kinesis_stream = kinesis.Stream(self, f"{iot_thing}_Stream", shard_count=1)
        kinesis_stream.grant_read_write(iot_role)

        log_group = logs.LogGroup(self, "Log Group")
        log_group.grant_write(iot_role)

        cfn_topic_rule = iot.CfnTopicRule(
            self,
            "MyCfnTopicRule",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                actions=[
                    iot.CfnTopicRule.ActionProperty(
                        kinesis=iot.CfnTopicRule.KinesisActionProperty(
                            role_arn=iot_role.role_arn,
                            stream_name=kinesis_stream.stream_name,
                            # the properties below are optional
                            # partition_key="partitionKey"
                        ),
                    ),
                ],
                sql=f"SELECT * FROM 'test'",
                error_action=iot.CfnTopicRule.ActionProperty(
                    cloudwatch_logs=iot.CfnTopicRule.CloudwatchLogsActionProperty(
                        log_group_name=log_group.log_group_name,
                        role_arn=iot_role.role_arn,
                    ),
                ),
            ),
        )

        polar_lambda = lambda_.Function(
            self,
            "PolarLambda",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="main.handler",
            code=lambda_.Code.from_asset(polar_dirname),
            memory_size=1024,
        )

        polar_lambda.add_event_source(
            KinesisEventSource(
                kinesis_stream,
                batch_size=10,
                starting_position=lambda_.StartingPosition.LATEST,
                max_batching_window=Duration.minutes(3),
            )
        )
        health_statistic_table = dynamodb.Table(
            self,
            "HealthStaticTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            stream=dynamodb.StreamViewType.NEW_IMAGE,
        )
        health_statistic_table.grant_read_write_data(polar_lambda)
        polar_lambda.add_environment("TableName", health_statistic_table.table_name)
        polar_lambda.add_environment("ThingName", iot_thing.thing_name)

        lambda_db = lambda_.Function(
            self,
            "LambdaDb",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="main.handler",
            code=lambda_.Code.from_asset(lambda_db_dirname),
            memory_size=1024,
        )
        lambda_db.add_event_source(
            DynamoEventSource(
                health_statistic_table,
                starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            )
        )

        my_topic = sns.Topic(self, f"{iot_thing.thing_name}_topic")

        # sns.Subscription(self, "Subscription",
        #     topic=my_topic,
        #     endpoint="+21627418181",
        #     protocol=sns.SubscriptionProtocol.SMS,
        #     subscription_role_arn="SAMPLE_ARN"
        # )

        sns.Subscription(self, "Subscription",
            topic=my_topic,
            endpoint="bouissihamza6@gmail.com",
            protocol=sns.SubscriptionProtocol.EMAIL,
        )

        my_topic.grant_publish(lambda_db)
        lambda_db.add_environment("TopicArn", my_topic.topic_arn)



        cert = f"arn:aws:iot:{self.region}:{self.account}:cert/5f116d509d0b9d2658ca826b4754314fa4da08cfbb20a7c245beef8f8143a0d0"

        cfn_policy_principal_attachment = iot.CfnPolicyPrincipalAttachment(
            self,
            "MyCfnPolicyPrincipalAttachment",
            policy_name=iot_cert_policy.policy_name,
            principal=cert,
        )
        cfn_policy_principal_attachment.add_dependency(iot_cert_policy)

        cfn_thing_principal_attachment = iot.CfnThingPrincipalAttachment(
            self,
            "MyCfnThingPrincipalAttachment",
            principal=cert,
            thing_name=iot_thing.thing_name,
        )
        cfn_thing_principal_attachment.add_dependency(iot_thing)

        CfnOutput(self, "GraphQLAPI", value=api.graphql_url)
        CfnOutput(self, "GraphQLAPIKey", value=api.api_key or "")



def create_resource_for_user(username:str):
    pass