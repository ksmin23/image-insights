# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

from aws_cdk import (
  core,
  aws_ec2,
  aws_s3 as s3,
  aws_apigateway as apigw,
  aws_iam,
  aws_lambda as _lambda,
  aws_kinesis as kinesis,
  aws_logs,
  aws_elasticsearch
)

from aws_cdk.aws_lambda_event_sources import (
  S3EventSource,
  KinesisEventSource
)

S3_BUCKET_LAMBDA_LAYER_LIB = os.getenv('S3_BUCKET_LAMBDA_LAYER_LIB', 'november-photo-resources')

class NovemberPhotoStack(core.Stack):

  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    # The code that defines your stack goes here
    vpc = aws_ec2.Vpc(self, "NovemberVPC",
      max_azs=2,
#      subnet_configuration=[{
#          "cidrMask": 24,
#          "name": "Public",
#          "subnetType": aws_ec2.SubnetType.PUBLIC,
#        },
#        {
#          "cidrMask": 24,
#          "name": "Private",
#          "subnetType": aws_ec2.SubnetType.PRIVATE
#        },
#        {
#          "cidrMask": 28,
#          "name": "Isolated",
#          "subnetType": aws_ec2.SubnetType.ISOLATED,
#          "reserved": True
#        }
#      ],
      gateway_endpoints={
        "S3": aws_ec2.GatewayVpcEndpointOptions(
          service=aws_ec2.GatewayVpcEndpointAwsService.S3
        )
      }
    )

    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name="november-photo-{region}-{account}".format(region=kwargs['env'].region, account=kwargs['env'].account))

    api = apigw.RestApi(self, "ImageAutoTaggerUploader",
      rest_api_name="ImageAutoTaggerUploader",
      description="This service serves uploading bizcard images into s3.",
      endpoint_types=[apigw.EndpointType.REGIONAL],
      binary_media_types=["image/png", "image/jpg"],
      deploy=True,
      deploy_options=apigw.StageOptions(stage_name="v1")
    )

    rest_api_role = aws_iam.Role(self, "ApiGatewayRoleForS3",
      role_name="ApiGatewayRoleForS3FullAccess",
      assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
      managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")]
    )

    list_objects_responses = [apigw.IntegrationResponse(status_code="200",
        #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationResponse.html#aws_cdk.aws_apigateway.IntegrationResponse.response_parameters
        # The response parameters from the backend response that API Gateway sends to the method response.
        # Use the destination as the key and the source as the value:
        #  - The destination must be an existing response parameter in the MethodResponse property.
        #  - The source must be an existing method request parameter or a static value.
        response_parameters={
          'method.response.header.Timestamp': 'integration.response.header.Date',
          'method.response.header.Content-Length': 'integration.response.header.Content-Length',
          'method.response.header.Content-Type': 'integration.response.header.Content-Type'
        }
      ),
      apigw.IntegrationResponse(status_code="400", selection_pattern="4\d{2}"),
      apigw.IntegrationResponse(status_code="500", selection_pattern="5\d{2}")
    ]

    list_objects_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses
    )

    get_s3_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path='/',
      options=list_objects_integration_options
    )

    api.root.add_method("GET", get_s3_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.EmptyModel()
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False
      }
    )

    get_s3_folder_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses,
      #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationOptions.html#aws_cdk.aws_apigateway.IntegrationOptions.request_parameters
      # Specify request parameters as key-value pairs (string-to-string mappings), with a destination as the key and a source as the value.
      # The source must be an existing method request parameter or a static value.
      request_parameters={"integration.request.path.bucket": "method.request.path.folder"}
    )

    get_s3_folder_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path="{bucket}",
      options=get_s3_folder_integration_options
    )

    s3_folder = api.root.add_resource('{folder}')
    s3_folder.add_method("GET", get_s3_folder_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.EmptyModel()
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True
      }
    )

    get_s3_item_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses,
      request_parameters={
        "integration.request.path.bucket": "method.request.path.folder",
        "integration.request.path.object": "method.request.path.item"
      }
    )

    get_s3_item_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path="{bucket}/{object}",
      options=get_s3_item_integration_options
    )

    s3_item = s3_folder.add_resource('{item}')
    s3_item.add_method("GET", get_s3_item_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.EmptyModel()
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True,
        'method.request.path.item': True
      }
    )

    put_s3_item_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=[apigw.IntegrationResponse(status_code="200"),
        apigw.IntegrationResponse(status_code="400", selection_pattern="4\d{2}"),
        apigw.IntegrationResponse(status_code="500", selection_pattern="5\d{2}")
      ],
      request_parameters={
        "integration.request.header.Content-Type": "method.request.header.Content-Type",
        "integration.request.path.bucket": "method.request.path.folder",
        "integration.request.path.object": "method.request.path.item"
      }
    )

    put_s3_item_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="PUT",
      path="{bucket}/{object}",
      options=put_s3_item_integration_options
    )

    s3_item.add_method("PUT", put_s3_item_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.EmptyModel()
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True,
        'method.request.path.item': True
      }
    )

    img_kinesis_stream = kinesis.Stream(self, "ImageAutoTaggerUploadedImagePath", stream_name="image-auto-tagger-img")

    # create lambda function
    trigger_img_tagger_lambda_fn = _lambda.Function(self, "TriggerImageAutoTagger",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="TriggerImageAutoTagger",
      handler="trigger_image_auto_tagger.lambda_handler",
      description="Trigger to recognize an image in S3",
      code=_lambda.Code.asset("./src/main/python/TriggerImageAutoTagger"),
      environment={
        'REGION_NAME': kwargs['env'].region,
        'KINESIS_STREAM_NAME': img_kinesis_stream.stream_name
      },
      timeout=core.Duration.minutes(5)
    )

    trigger_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[img_kinesis_stream.stream_arn],
      actions=["kinesis:Get*",
        "kinesis:List*",
        "kinesis:Describe*",
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ]
    ))

    # assign notification for the s3 event type (ex: OBJECT_CREATED)
    s3_event_filter = s3.NotificationKeyFilter(prefix="raw-image/", suffix=".jpg")
    s3_event_source = S3EventSource(s3_bucket, events=[s3.EventType.OBJECT_CREATED], filters=[s3_event_filter])
    trigger_img_tagger_lambda_fn.add_event_source(s3_event_source)

    #XXX: https://github.com/aws/aws-cdk/issues/2240
    # To avoid to create extra Lambda Functions with names like LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a
    # if log_retention=aws_logs.RetentionDays.THREE_DAYS is added to the constructor props
    log_group = aws_logs.LogGroup(self, "TriggerImageAutoTaggerLogGroup",
      log_group_name="/aws/lambda/TriggerImageAutoTagger",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(trigger_img_tagger_lambda_fn)

    sg_use_es = aws_ec2.SecurityGroup(self, "ImageTagSearchClientSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for elasticsearch client of image tagger',
      security_group_name='use-image-tagger-es'
    )
    core.Tag.add(sg_use_es, 'Name', 'sg-use-image-tagger-es')

    sg_es = aws_ec2.SecurityGroup(self, "ImageTagSearchSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for elasticsearch of image tag',
      security_group_name='image-tagger-es'
    )
    core.Tag.add(sg_es, 'Name', 'sg-image-tagger-es')

    sg_es.add_ingress_rule(peer=sg_es, connection=aws_ec2.Port.all_tcp(), description='image-tagger-es')
    sg_es.add_ingress_rule(peer=sg_use_es, connection=aws_ec2.Port.all_tcp(), description='use-image-tagger-es')

    #XXX: aws cdk elastsearch example - https://github.com/aws/aws-cdk/issues/2873
    es_cfn_domain = aws_elasticsearch.CfnDomain(self, 'ImageTagSearch',
      elasticsearch_cluster_config={
        "dedicatedMasterCount": 3,
        "dedicatedMasterEnabled": True,
        "dedicatedMasterType": "t2.medium.elasticsearch",
        "instanceCount": 2,
        "instanceType": "t2.medium.elasticsearch",
        "zoneAwarenessEnabled": True
      },
      ebs_options={
        "ebsEnabled": True,
        "volumeSize": 10,
        "volumeType": "gp2"
      },
      domain_name="november-pictos",
      elasticsearch_version="7.1",
      encryption_at_rest_options={
        "enabled": False
      },
      access_policies={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
              "AWS": "*"
            },
            "Action": [
              "es:Describe*",
              "es:List*",
              "es:Get*",
              "es:ESHttp*"
            ],
            "Resource": self.format_arn(service="es", resource="domain", resource_name="november-pictos/*")
          }
        ]
      },
      snapshot_options={
        "automatedSnapshotStartHour": 17
      },
      vpc_options={
        "securityGroupIds": [sg_es.security_group_id],
        "subnetIds": vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
      }
    )
    core.Tag.add(es_cfn_domain, 'Name', 'image-tagger-es')

    #XXX: https://github.com/aws/aws-cdk/issues/1342
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, id, S3_BUCKET_LAMBDA_LAYER_LIB)
    es_lib_layer = _lambda.LayerVersion(self, "ESLib",
      layer_version_name="es-lib",
      compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
      code=_lambda.Code.from_bucket(s3_lib_bucket, "var/es-lib.zip")
    )

    #XXX: Deploy lambda in VPC - https://github.com/aws/aws-cdk/issues/1342
    auto_img_tagger_lambda_fn = _lambda.Function(self, "AutomaticImageTagger",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="AutomaticImageTagger",
      handler="image_auto_tagger.lambda_handler",
      description="Automatically tag images",
      code=_lambda.Code.asset("./src/main/python/ImageAutoTagger"),
      environment={
        'ES_HOST': es_cfn_domain.attr_domain_endpoint,
        'ES_INDEX': 'november_photo',
        'ES_TYPE': 'photo'
      },
      timeout=core.Duration.minutes(5),
      layers=[es_lib_layer],
      security_groups=[sg_use_es],
      vpc=vpc
    )

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["rekognition:*"]))

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["s3:Get*", "s3:List*"]))

    img_kinesis_event_source = KinesisEventSource(img_kinesis_stream, batch_size=100, starting_position=_lambda.StartingPosition.LATEST)
    auto_img_tagger_lambda_fn.add_event_source(img_kinesis_event_source)

    log_group = aws_logs.LogGroup(self, "AutomaticImageTaggerLogGroup",
      log_group_name="/aws/lambda/AutomaticImageTagger",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(auto_img_tagger_lambda_fn)

