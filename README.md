# Project Description

- Amazon Rekognition을 활용한 이미지 자동 태킹 및 이미지 태그 데이터 시각화 서비스
- (1) 아래와 같이 이미지를 업로드 하면,
![demo_upload_image_files](resources/demo-upload-image-files.png)
- (2) 다음과 같이 이미지 태그 데이터의 분석 결과를 보여준다.
![demo_image_tags_visualization](resources/demo-image-tags-visualization.png)


### Architecture
![auto_image_tagger-architecture](auto_image_tagger_arch.png)

##### Key AWS Services
- API Gateway
- Lambda Function
- Kinesis Data Stream
- Elasticsearch Service
- Rekognition
- S3


### RESTful API Specification
##### Image upload
- Request
  - PUT
    ```
    - /v1/{bucket}/{object}
    ```

    | URL Path parameters | Description | Required(Yes/No) | Data Type |
    |---------------------|-------------|------------------|-----------|
    | bucket | s3 bucket 이름 | Yes | String |
    | object | s3 object 이름 | Yes | String |

  - ex)
    ```
    curl -X PUT "https://t2e7cpvqvu.execute-api.us-east-1.amazonaws.com/v1/image-vaults/raw-image%2F20191101_125236.jpg" \
         --data @20191101_125236.jpg
    ```

- Response
  - No Data


### How To Build & Deploy
1. [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)를 참고해서 cdk를 설치하고,
cdk를 실행할 때 사용할 IAM User를 생성한 후, `~/.aws/config`에 등록함
예를 들어서, **cdk_user**라는 IAM User를 생성 한 후, 아래와 같이 `~/.aws/config`에 추가로 등록함

    ```shell script
    $ cat ~/.aws/config
    [profile cdk_user]
    aws_access_key_id=AKIAIOSFODNN7EXAMPLE
    aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region=us-east-1
    ```
    :information_source: **cdk_user** 는 임시로 `AdministratorAccess` 권한을 부여한다.

2. Lambda Layer에 등록할 Python 패키지를 생성해서 s3 bucket에 저장함
에를 들어, elasticsearch 패키지를 Lambda Layer에 등록 할 수 있도록 image-insights-resources라는 이름의 s3 bucket을 생성 후, 아래와 같이 저장함

    ```shell script
    $ aws s3 ls s3://image-insights-resources/var/
    2019-10-25 08:38:50          0
    2019-10-25 08:40:28    1294387 es-lib.zip
    ```

3. 소스 코드를 git에서 다운로드 받은 후, 아래와 같이 cdk 배포 환경을 구축함

    ```shell script
    $ git clone https://github.com/ksmin23/image-insights.git
    $ cd image-insights
    $ python3 -m venv .env
    $ source .env/bin/activate
    (.env) $ pip install -r requirements.txt
    ```

4. 아래와 같이 S3에 Read/Write를 할 수 있는 권한을 갖는 IAM User를 생성한 후, Access Key Id와 Secrect Key를 다운로드 받음
   
   ```json
   {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject*",
                "s3:ListObject*",
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "*"
        }
    ]
   }
   ```

5. `cdk.context.json` 파일을 열어서, `lib_bucket_name`에 Lambda Layer에 등록할 Python 패키지가 저장된 s3 bucket 이름을 적고,<br/>`image_bucket_name_suffix`에 업로드 된 이미지를
저장하는 s3 bucket의 suffix를 넣는다.<br/>

    ```json
    {
      "image_bucket_name_suffix": "Your-S3-Bucket-Name-Suffix",
      "lib_bucket_name": "Your-S3-Bucket-Name-Of-Lib",
      "s3_access_key_id": "Access-Key-Of-Your-IAM-User-Allowed-To-Access-S3",
      "s3_secret_key": "Secret-Key-Of-Your-IAM-User-Allowed-To-Access-S3"
    }
    ```

6. `cdk deploy` 명령어를 이용해서 배포한다.
    ```shell script
    (.env) $ cdk --profile=cdk_user deploy
    ```

7. 배포한 애플리케이션을 삭제하려면, `cdk destroy` 명령어를 아래와 같이 실행
    ```shell script
    (.env) $ cdk --profile cdk_user destroy
    ```

8. 배포가 완료되면, API Gateway 웹 콘솔 접속해서 이미지 Uploader API의 **Binary Media Types** 설정이
   정상적으로 되어 있는지 확인함
   ![apigw-binary-media-types-setting](resources/apigw-binary-media-types-setting.png)

9.  (Optional) VPC내에 생성된 ElasticSearch cluster에 ssh tunnel을 이용해서 접근할 수 있도록 위에서 생성한 VPC의 public subnet에 bastion host (ec2 인스턴스)가 생성되었는지 확인함
    ![ec2-bastion-host-info](resources/ec2-bastion-host-info.png)

10. (Optional) bastion host에서 사용 할 ssh key를 다음과 같이 생성함
    ```shell script
    $ cd ~/.ssh
    $ ssh-keygen
    Generating public/private rsa key pair.
    Enter file in which to save the key (~/.ssh/id_rsa): MY-KEY
    Enter passphrase (empty for no passphrase):
    Enter same passphrase again:
    Your identification has been saved in MY-KEY.
    Your public key has been saved in MY-KEY.pub.
    The key fingerprint is:
    SHA256:NjRiNGM1MzY2NmM5NjY1Yjc5ZDBhNTdmMGU0NzZhZGF
    The key's randomart image is:
    +---[RSA 3072]----+
    |E*B++o           |
    |B= = ..          |
    |**o +            |
    |B=+  o           |
    |B+=oo . S        |
    |+@o+ o .         |
    |*.+o  .          |
    |.oo              |
    |  o.             |
    +----[SHA256]-----+
    $ ls -1 MY-KEY*
    MY-KEY
    MY-KEY.pub
    ```

11. (Optional) local 컴퓨터의 ssh config file에 아래 내용을 추가함 (`~/.ssh/config` on Mac, Linux)
    ```shell script
    # Elasticsearch Tunnel
    Host estunnel
      HostName 12.34.56.78 # your server's public IP address
      User ec2-user # your servers' user name
      IdentitiesOnly yes
      IdentityFile ~/.ssh/MY-KEY # your servers' key pair
      LocalForward 9200 vpc-YOUR-ES-CLUSTER.us-east-1.es.amazonaws.com:443 # your ElasticSearch cluster endpoint
    ```

12. (Optional) 다음과 같은 방식으로 ssh로 bastion host에 접근 할 수 있도록, public key를 bastion host에 보냄
    ```shell script
    $ cat send_ssh_publick_key.sh
    #!/bin/bash -

    REGION=us-east-1 # Your Region
    INSTANCE_ID=i-xxxxxxxxxxxxxxxxx # Your Bastion Host Instance Id
    AVAIL_ZONE=us-east-1a # Your AZ
    SSH_PUBLIC_KEY=${HOME}/.ssh/MY-KEY.pub # Your SSH Publikc Key location

    aws ec2-instance-connect send-ssh-public-key \
        --region ${REGION} \
        --instance-os-user ec2-user \
        --instance-id ${INSTANCE_ID} \
        --availability-zone ${AVAIL_ZONE} \
        --ssh-public-key file://${SSH_PUBLIC_KEY}

    $ bash send_ssh_publick_key.sh
    {
        "RequestId": "af8c63b9-90b3-48a9-9cb5-b242ec2c34ad",
        "Success": true
    }
    ```

13. (Optional) local 컴퓨터에서 `ssh -N estunnel` 명령어를 실행함
    ```shell script
    $ ssh -N estunnel
    ```

14. (Optional) local 컴퓨터의 web browser (Chrome, Firefox 등)에서 아래 URL로 접속하면, ElasticSearch와 Kibana에 접근 할 수 있음
    - Search: `https://localhost:9200/`
    - Kibana: `https://localhost:9200/_plugin/kibana/`


### Kibana dashboards 그리기
1. local 컴퓨터의 web browser (Chrome, Firefox 등)에서 `https://localhost:9200/_plugin/kibana/` 로 접속함
2. Kibana toolbar에서 Managemant > Index Patterns 메뉴를 선택 해서, Index Pattern을 생성함 (예: image_insights)<br/>
    - (1) ![kibana-index-patterns-01](resources/kibana-index-patterns-01.png)
    - (2) ![kibana-index-patterns-02](resources/kibana-index-patterns-02.png)

3. Kibana toolbar에서 Visualize 메뉴를 선택 함 (다음 순서로 그래프를 그림)<br/>
    (a) Image Count 그리기
    - (1) ![kibana-visualize-01](resources/kibana-visualize-01.png)
    - (2) ![kibana-visualize-img-count-02](resources/kibana-visualize-img-count-02.png)
    - (3) ![kibana-visualize-img-count-03](resources/kibana-visualize-img-count-03.png)
    - (4) ![kibana-visualize-img-count-04](resources/kibana-visualize-img-count-04.png)

    (b) Tag Cloud 그리기
    - (1) ![kibana-visualize-tag-cloud-01](resources/kibana-visualize-tag-cloud-01.png)
    - (2) ![kibana-visualize-tag-cloud-02](resources/kibana-visualize-tag-cloud-02.png)
    - (3) ![kibana-visualize-tag-cloud-03](resources/kibana-visualize-tag-cloud-03.png)

    (c) Tag Count 그리기
    - (1) ![kibana-visualize-tag-count-01](resources/kibana-visualize-tag-count-01.png)
    - (2) ![kibana-visualize-tag-count-02](resources/kibana-visualize-tag-count-02.png)
    - (3) ![kibana-visualize-tag-count-03](resources/kibana-visualize-tag-count-03.png)

    (d) Tag Pie Chart 그리기<br/>
    - (1) ![kibana-visualize-tag-pie-chart-01](resources/kibana-visualize-tag-pie-chart-01.png)
    - (2) ![kibana-visualize-tag-pie-chart-02](resources/kibana-visualize-tag-pie-chart-02.png)
    - (3) ![kibana-visualize-tag-pie-chart-03](resources/kibana-visualize-tag-pie-chart-03.png)

4. Kibana toolbar에서 Dashboard 메뉴를 선택 함 (다음 순서로 Dashboard에 앞서 생성한 그래프를 추가함)<br/>
    - (1) ![kibana-dashboard-01](resources/kibana-dashboard-01.png)
    - (2) ![kibana-dashboard-02](resources/kibana-dashboard-02.png)
    - (3) ![kibana-dashboard-03](resources/kibana-dashboard-03.png)


### Demo
##### 이미지를 등록하는 방법

- **Postman을 이용해서 이미지 업로드 API로 명함을 등록하는 방법**

  1. Postman에서 아래 그림과 같이 Authorization 탭에서 TYPE을 AWS Signature로 선택하고, S3 Read/Write 권한을 가진 사용자의 
 AccessKey, SecretKey를 등록하고, AWS Region을 설정함<br/>
  ![img-uploader-01](resources/img-uploader-01.png)
  2. Headers 탭을 선택하고, Key, Value를 아래 그림과 같이 추가함<br/>
  ![img-uploader-02](resources/img-uploader-02.png)
  3. Body 탭에서 binary를 선택하고, Select File 버튼을 눌러서, 전송할 파일을 추가함<br/>
  ![img-uploader-02](resources/img-uploader-03.png)
  4. 전송할 이미지 파일이 추가한 후, Send 버튼을 눌러서 PUT 메소드를 실행함<br/>
  ![img-uploader-02](resources/img-uploader-04.png)

- **demo용 클라이언트를 사용하는 방법**

  1. 업로드한 명함 이미지를 저장할 s3 bucket의 CORS 설정을 아래 처럼 변경함
        ```
        [
            {
                "AllowedHeaders": [
                    "Authorization"
                ],
                "AllowedMethods": [
                    "GET",
                    "POST"
                ],
                "AllowedOrigins": [
                    "*"
                ],
                "ExposeHeaders": [],
                "MaxAgeSeconds": 3000
            }
        ]
        ```
        - ex)
           ![s3_bucket_cors_configuration](resources/s3_bucket_cors_configuration_json.png)

   2. [Serverless S3 Upload with Lambda Demo](https://github.com/Beomi/s3-direct-uploader-demo) 를 로컬 PC에 git clone 한 후, `app.js` 파일에서 `//TODO` 부분을 알맞게 수정함

        ```js
        var uploader = new qq.s3.FineUploader({
            debug: false, // defaults to false
            element: document.getElementById('fine-uploader'),
            request: {
                //TODO: S3 Bucket URL
                endpoint: 'https://{s3-bucket-name}.s3.amazonaws.com',
                //TODO: IAM User AccessKey
                accessKey: '{IAM User AccessKey}'
            },
            objectProperties: {
                //TODO: AWS Region name
                region: '{region-name}',
                key(fileId) {
                    //TODO: S3 Bucket Prefix
                    var prefixPath = '{s3-bucket-prefix}'
                    var filename = this.getName(fileId)
                    return prefixPath + '/' + filename
                }
            },
            signature: {
                // version
                version: 4,
                //TODO: AWS API Gateway Lambda Authorizers URL
                endpoint: 'https://{api-gateway-id}.execute-api.{region-name}.amazonaws.com/{api-gateway-version}'
            },
            retry: {
                enableAuto: true // defaults to false
            }
        });
        ```

   3. 수정한 이후, `index.html` 파일을 browser로 열어서 사용함
