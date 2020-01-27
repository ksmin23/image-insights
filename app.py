#!/usr/bin/env python3
import os

from aws_cdk import core

from november_photo.november_photo_stack import NovemberPhotoStack


ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT', '')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
AWS_ENV = core.Environment(account=ACCOUNT, region=REGION)

app = core.App()
#NovemberPhotoStack(app, "november-photo")
NovemberPhotoStack(app, "november-photo", env=AWS_ENV)

app.synth()
