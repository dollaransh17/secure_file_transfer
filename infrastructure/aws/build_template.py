"""Generate the reviewable AWS CloudFormation deployment. Never calls AWS APIs."""
import json
from pathlib import Path

R={}
def ref(name):return {'Ref':name}
def sub(value):return {'Fn::Sub':value}
def get(name,attribute):return {'Fn::GetAtt':[name,attribute]}
def add(name,kind,properties,**extra):
    R[name]={'Type':'AWS::'+kind,'Properties':properties,**extra};return ref(name)
def env(values):return [{'Name':key,'Value':value} for key,value in values.items()]
def secret(name,arn,key):return {'Name':name,'ValueFrom':{'Fn::Join':['',[arn,':'+key+'::']]}}

def generate():
    R.clear()
    params={
      'ProjectName':{'Type':'String','Default':'prooflane','AllowedPattern':'[a-z][a-z0-9-]{2,23}'},
      'DomainName':{'Type':'String','Description':'Existing DNS name covered by the ACM certificate; create its ALIAS record after deployment'},
      'CertificateArn':{'Type':'String','AllowedPattern':'arn:aws:acm:.*','Description':'Existing regional ACM certificate'},
      'ApiImage':{'Type':'String','AllowedPattern':'.+@sha256:[a-f0-9]{64}','Description':'Digest-pinned ECR URI for the API image'},
      'WebImage':{'Type':'String','AllowedPattern':'.+@sha256:[a-f0-9]{64}','Description':'Digest-pinned ECR URI for the frontend image'},
      'WorkerImage':{'Type':'String','Default':'','AllowedPattern':'^$|.+@sha256:[a-f0-9]{64}','Description':'Optional ML-enabled ECR image; empty uses ApiImage'},
      'Architecture':{'Type':'String','Default':'ARM64','AllowedValues':['ARM64','X86_64']},
      'AnthropicSecretArn':{'Type':'String','Default':'','Description':'Optional existing Secrets Manager JSON secret with ANTHROPIC_API_KEY; key is never a template parameter'},
      'AnthropicModel':{'Type':'String','Default':'','Description':'Configured account-supported model ID, validated at request time'},
      'DatabaseClass':{'Type':'String','Default':'db.t4g.micro'},
      'CacheClass':{'Type':'String','Default':'cache.t4g.micro'},
      'ClamavImage':{'Type':'String','Default':'clamav/clamav:1.5.4-debian13-slim'},
    }
    az=lambda i:{'Fn::Select':[i,{'Fn::GetAZs':''}]}
    add('Vpc','EC2::VPC',{'CidrBlock':'10.84.0.0/16','EnableDnsSupport':True,'EnableDnsHostnames':True})
    add('Internet','EC2::InternetGateway',{})
    add('InternetAttachment','EC2::VPCGatewayAttachment',{'VpcId':ref('Vpc'),'InternetGatewayId':ref('Internet')})
    for suffix,index in [('A',0),('B',1)]:
        add('Public'+suffix,'EC2::Subnet',{'VpcId':ref('Vpc'),'CidrBlock':f'10.84.{index}.0/24','AvailabilityZone':az(index),'MapPublicIpOnLaunch':False})
        add('Private'+suffix,'EC2::Subnet',{'VpcId':ref('Vpc'),'CidrBlock':f'10.84.{10+index}.0/24','AvailabilityZone':az(index),'MapPublicIpOnLaunch':False})
    add('PublicRoutes','EC2::RouteTable',{'VpcId':ref('Vpc')})
    add('PublicDefault','EC2::Route',{'RouteTableId':ref('PublicRoutes'),'DestinationCidrBlock':'0.0.0.0/0','GatewayId':ref('Internet')},DependsOn='InternetAttachment')
    for suffix in ['A','B']:
        add('PublicAssociation'+suffix,'EC2::SubnetRouteTableAssociation',{'SubnetId':ref('Public'+suffix),'RouteTableId':ref('PublicRoutes')})
    add('NatAddress','EC2::EIP',{'Domain':'vpc'},DependsOn='InternetAttachment')
    add('Nat','EC2::NatGateway',{'AllocationId':get('NatAddress','AllocationId'),'SubnetId':ref('PublicA')})
    add('PrivateRoutes','EC2::RouteTable',{'VpcId':ref('Vpc')})
    add('PrivateDefault','EC2::Route',{'RouteTableId':ref('PrivateRoutes'),'DestinationCidrBlock':'0.0.0.0/0','NatGatewayId':ref('Nat')})
    for suffix in ['A','B']:
        add('PrivateAssociation'+suffix,'EC2::SubnetRouteTableAssociation',{'SubnetId':ref('Private'+suffix),'RouteTableId':ref('PrivateRoutes')})
    add('AlbSecurity','EC2::SecurityGroup',{'GroupDescription':'HTTPS ingress and HTTP redirect','VpcId':ref('Vpc'),'SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':p,'ToPort':p,'CidrIp':'0.0.0.0/0'} for p in [80,443]]})
    add('TaskSecurity','EC2::SecurityGroup',{'GroupDescription':'Only ALB and internal application traffic','VpcId':ref('Vpc')})
    for port in [80,8000]:add('AlbToTask'+str(port),'EC2::SecurityGroupIngress',{'GroupId':ref('TaskSecurity'),'IpProtocol':'tcp','FromPort':port,'ToPort':port,'SourceSecurityGroupId':ref('AlbSecurity')})
    for port in [3310,8000]:add('InternalTask'+str(port),'EC2::SecurityGroupIngress',{'GroupId':ref('TaskSecurity'),'IpProtocol':'tcp','FromPort':port,'ToPort':port,'SourceSecurityGroupId':ref('TaskSecurity')})
    for name,port in [('Database',5432),('Cache',6379)]:
        add(name+'Security','EC2::SecurityGroup',{'VpcId':ref('Vpc'),'GroupDescription':'Private '+name,'SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':port,'ToPort':port,'SourceSecurityGroupId':ref('TaskSecurity')}]})
    bucket_name='${ProjectName}-${AWS::AccountId}-${AWS::Region}-files'
    bucket_arn='arn:${AWS::Partition}:s3:::'+bucket_name
    add('StorageKey','KMS::Key',{'EnableKeyRotation':True,'KeyPolicy':{'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Principal':{'AWS':sub('arn:${AWS::Partition}:iam::${AWS::AccountId}:root')},'Action':'kms:*','Resource':'*'}
    ]}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
    # Separate queue encryption from object encryption. This service grant follows
    # AWS's documented S3 notification KMS policy; the queue policy below binds
    # publishing to this bucket/account. The API cannot use the event key.
    add('EventKey','KMS::Key',{'EnableKeyRotation':True,'KeyPolicy':{'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Principal':{'AWS':sub('arn:${AWS::Partition}:iam::${AWS::AccountId}:root')},'Action':'kms:*','Resource':'*'},
        {'Effect':'Allow','Principal':{'Service':'s3.amazonaws.com'},'Action':['kms:GenerateDataKey','kms:Decrypt'],'Resource':'*'}
    ]}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
    add('EventDeadLetter','SQS::Queue',{'MessageRetentionPeriod':1209600,'SqsManagedSseEnabled':True})
    add('StorageEvents','SQS::Queue',{'KmsMasterKeyId':get('EventKey','Arn'),'VisibilityTimeout':180,'ReceiveMessageWaitTimeSeconds':20,'RedrivePolicy':{'deadLetterTargetArn':get('EventDeadLetter','Arn'),'maxReceiveCount':5}})
    add('StorageQueuePolicy','SQS::QueuePolicy',{'Queues':[ref('StorageEvents')],'PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'s3.amazonaws.com'},'Action':'sqs:SendMessage','Resource':get('StorageEvents','Arn'),'Condition':{'ArnEquals':{'aws:SourceArn':sub(bucket_arn)},'StringEquals':{'aws:SourceAccount':ref('AWS::AccountId')}}}]}})
    add('Files','S3::Bucket',{'BucketName':sub(bucket_name),'VersioningConfiguration':{'Status':'Enabled'},'OwnershipControls':{'Rules':[{'ObjectOwnership':'BucketOwnerEnforced'}]},'PublicAccessBlockConfiguration':{'BlockPublicAcls':True,'BlockPublicPolicy':True,'IgnorePublicAcls':True,'RestrictPublicBuckets':True},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'aws:kms','KMSMasterKeyID':get('StorageKey','Arn')},'BucketKeyEnabled':True}]},'NotificationConfiguration':{'QueueConfigurations':[{'Event':'s3:ObjectCreated:*','Queue':get('StorageEvents','Arn')}] }},DependsOn='StorageQueuePolicy',DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
    add('FilesPolicy','S3::BucketPolicy',{'Bucket':ref('Files'),'PolicyDocument':{'Version':'2012-10-17','Statement':[
        {'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[sub(bucket_arn),sub(bucket_arn+'/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}},
        {'Effect':'Deny','Principal':'*','Action':'s3:PutObject','Resource':sub(bucket_arn+'/*'),'Condition':{'StringNotEquals':{'s3:x-amz-server-side-encryption':'aws:kms'}}},
        {'Effect':'Deny','Principal':'*','Action':'s3:PutObject','Resource':sub(bucket_arn+'/*'),'Condition':{'StringNotEquals':{'s3:x-amz-server-side-encryption-aws-kms-key-id':get('StorageKey','Arn')}}}
    ]}})
    add('DatabaseSubnet','RDS::DBSubnetGroup',{'DBSubnetGroupDescription':'Private Prooflane database','SubnetIds':[ref('PrivateA'),ref('PrivateB')]})
    add('Database','RDS::DBInstance',{'Engine':'postgres','DBInstanceClass':ref('DatabaseClass'),'AllocatedStorage':'20','StorageType':'gp3','StorageEncrypted':True,'DBName':'prooflane','MasterUsername':'prooflane','ManageMasterUserPassword':True,'DBSubnetGroupName':ref('DatabaseSubnet'),'VPCSecurityGroups':[ref('DatabaseSecurity')],'PubliclyAccessible':False,'BackupRetentionPeriod':7,'DeletionProtection':True,'AutoMinorVersionUpgrade':True},DeletionPolicy='Snapshot',UpdateReplacePolicy='Snapshot')
    add('CacheSecret','SecretsManager::Secret',{'GenerateSecretString':{'SecretStringTemplate':'{}','GenerateStringKey':'password','PasswordLength':40,'ExcludePunctuation':True}})
    add('CacheSubnet','ElastiCache::SubnetGroup',{'Description':'Private Redis','SubnetIds':[ref('PrivateA'),ref('PrivateB')]})
    add('Cache','ElastiCache::ReplicationGroup',{'ReplicationGroupDescription':'Prooflane rate-limit counters','Engine':'redis','EngineVersion':'7.1','CacheNodeType':ref('CacheClass'),'NumCacheClusters':1,'CacheSubnetGroupName':ref('CacheSubnet'),'SecurityGroupIds':[ref('CacheSecurity')],'TransitEncryptionEnabled':True,'AtRestEncryptionEnabled':True,'AuthToken':sub('{{resolve:secretsmanager:${CacheSecret}:SecretString:password}}')})
    add('Logs','Logs::LogGroup',{'LogGroupName':sub('/prooflane/${ProjectName}'),'RetentionInDays':30})
    assume={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ecs-tasks.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    add('ExecutionRole','IAM::Role',{'AssumeRolePolicyDocument':assume,'ManagedPolicyArns':[sub('arn:${AWS::Partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy')],'Policies':[{'PolicyName':'ReadApplicationSecrets','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'secretsmanager:GetSecretValue','Resource':[get('Database','MasterUserSecret.SecretArn'),ref('CacheSecret'),{'Fn::If':['HasClaude',ref('AnthropicSecretArn'),ref('AWS::NoValue')]}]}]}}]})
    for name,actions in [('Api',['s3:GetObjectVersion','s3:PutObject']),('Worker',['s3:GetObjectVersion'])]:
        statements=[{'Effect':'Allow','Action':actions,'Resource':sub(bucket_arn+'/*')},{'Effect':'Allow','Action':'s3:GetBucketVersioning','Resource':sub(bucket_arn)},{'Effect':'Allow','Action':['kms:Decrypt','kms:GenerateDataKey','kms:DescribeKey'],'Resource':get('StorageKey','Arn')}]
        if name=='Worker':statements.append({'Effect':'Allow','Action':'kms:Decrypt','Resource':get('EventKey','Arn')})
        if name=='Worker':statements.append({'Effect':'Allow','Action':['sqs:ReceiveMessage','sqs:DeleteMessage','sqs:ChangeMessageVisibility','sqs:GetQueueAttributes'],'Resource':get('StorageEvents','Arn')})
        add(name+'Role','IAM::Role',{'AssumeRolePolicyDocument':assume,'Policies':[{'PolicyName':'ScopedStorage','PolicyDocument':{'Version':'2012-10-17','Statement':statements}}]})
    add('Cluster','ECS::Cluster',{'ClusterSettings':[{'Name':'containerInsights','Value':'enabled'}]})
    add('Namespace','ServiceDiscovery::PrivateDnsNamespace',{'Name':sub('${ProjectName}.internal'),'Vpc':ref('Vpc')})
    for name in ['Api','Clamav']:
        add(name+'Discovery','ServiceDiscovery::Service',{'Name':name.lower(),'NamespaceId':ref('Namespace'),'DnsConfig':{'DnsRecords':[{'Type':'A','TTL':10}]},'HealthCheckCustomConfig':{'FailureThreshold':1}})
    common={'ENVIRONMENT':'production','PUBLIC_ORIGIN':sub('https://${DomainName}'),'COOKIE_SECURE':'true','DATABASE_HOST':get('Database','Endpoint.Address'),'DATABASE_USER':'prooflane','DATABASE_NAME':'prooflane','DATABASE_SSLMODE':'verify-full','DATABASE_SSLROOTCERT':'/etc/ssl/certs/aws-rds-global.pem','REDIS_HOST':get('Cache','PrimaryEndPoint.Address'),'STORAGE_BACKEND':'s3','S3_ENDPOINT':'','S3_BUCKET':ref('Files'),'AWS_REGION':ref('AWS::Region'),'KMS_KEY_ID':get('StorageKey','Arn'),'CLAMAV_HOST':sub('clamav.${ProjectName}.internal'),'CLAMAV_PORT':'3310','MODEL_DIRECTORY':'/app/cloud-models','ANTHROPIC_MODEL':ref('AnthropicModel')}
    secrets=[secret('DATABASE_PASSWORD',get('Database','MasterUserSecret.SecretArn'),'password'),secret('REDIS_PASSWORD',ref('CacheSecret'),'password')]
    def task(name,image,cpu,memory,port=None,command=None,role=None,environment=None,secret_values=None,health=None):
        container={'Name':name.lower(),'Image':image,'Essential':True,'Environment':env(environment or {}),'LogConfiguration':{'LogDriver':'awslogs','Options':{'awslogs-group':ref('Logs'),'awslogs-region':ref('AWS::Region'),'awslogs-stream-prefix':name.lower()}}}
        if port:container['PortMappings']=[{'ContainerPort':port,'Protocol':'tcp'}]
        if command:container['Command']=command
        if secret_values:container['Secrets']=secret_values
        if health:container['HealthCheck']={'Command':['CMD-SHELL',health],'Interval':30,'Timeout':5,'Retries':5,'StartPeriod':120}
        props={'Family':sub('${ProjectName}-'+name.lower()),'Cpu':str(cpu),'Memory':str(memory),'NetworkMode':'awsvpc','RequiresCompatibilities':['FARGATE'],'RuntimePlatform':{'CpuArchitecture':ref('Architecture'),'OperatingSystemFamily':'LINUX'},'ExecutionRoleArn':get('ExecutionRole','Arn'),'ContainerDefinitions':[container]}
        if role:props['TaskRoleArn']=get(role,'Arn')
        add(name+'Task','ECS::TaskDefinition',props)
    api_secrets=secrets+[{'Fn::If':['HasClaude',secret('ANTHROPIC_API_KEY',ref('AnthropicSecretArn'),'ANTHROPIC_API_KEY'),ref('AWS::NoValue')]}]
    task('Api',ref('ApiImage'),512,1024,8000,['sh','-c','alembic upgrade head && exec uvicorn prooflane.main:app --host 0.0.0.0 --port 8000'],'ApiRole',common,api_secrets,"python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)\"")
    worker_env=dict(common,STORAGE_EVENT_QUEUE_URL=ref('StorageEvents'),WORKER_CAPACITY='2',TENANT_CAPACITY='2',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    task('Worker',{'Fn::If':['HasWorkerImage',ref('WorkerImage'),ref('ApiImage')]},1024,2048,command=['python','-m','prooflane.worker'],role='WorkerRole',environment=worker_env,secret_values=secrets)
    task('Clamav',ref('ClamavImage'),1024,4096,3310,health='clamdscan --ping 1')
    task('Web',ref('WebImage'),256,512,80,environment={'API_UPSTREAM':sub('api.${ProjectName}.internal:8000')},health='wget -q -O /dev/null http://127.0.0.1/api/health')
    add('Balancer','ElasticLoadBalancingV2::LoadBalancer',{'Scheme':'internet-facing','Subnets':[ref('PublicA'),ref('PublicB')],'SecurityGroups':[ref('AlbSecurity')],'Type':'application'})
    for name,port in [('Api',8000),('Web',80)]:
        add(name+'Target','ElasticLoadBalancingV2::TargetGroup',{'VpcId':ref('Vpc'),'Port':port,'Protocol':'HTTP','TargetType':'ip','HealthCheckPath':'/api/health','Matcher':{'HttpCode':'200'}})
    add('Https','ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('Balancer'),'Port':443,'Protocol':'HTTPS','SslPolicy':'ELBSecurityPolicy-TLS13-1-3-2021-06','Certificates':[{'CertificateArn':ref('CertificateArn')}],'DefaultActions':[{'Type':'forward','TargetGroupArn':ref('WebTarget')}]})
    add('ApiRoute','ElasticLoadBalancingV2::ListenerRule',{'ListenerArn':ref('Https'),'Priority':10,'Conditions':[{'Field':'path-pattern','Values':['/api/*']}],'Actions':[{'Type':'forward','TargetGroupArn':ref('ApiTarget')}]})
    add('HttpRedirect','ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('Balancer'),'Port':80,'Protocol':'HTTP','DefaultActions':[{'Type':'redirect','RedirectConfig':{'Protocol':'HTTPS','Port':'443','StatusCode':'HTTP_301'}}]})
    for name,count in [('Api',1),('Web',1),('Clamav',1),('Worker',2)]:
        properties={'Cluster':ref('Cluster'),'TaskDefinition':ref(name+'Task'),'DesiredCount':count,'LaunchType':'FARGATE','PlatformVersion':'LATEST','DeploymentConfiguration':{'DeploymentCircuitBreaker':{'Enable':True,'Rollback':True},'MaximumPercent':100,'MinimumHealthyPercent':0},'NetworkConfiguration':{'AwsvpcConfiguration':{'AssignPublicIp':'DISABLED','Subnets':[ref('PrivateA'),ref('PrivateB')],'SecurityGroups':[ref('TaskSecurity')]}}}
        if name in ('Api','Web'):properties['LoadBalancers']=[{'ContainerName':name.lower(),'ContainerPort':8000 if name=='Api' else 80,'TargetGroupArn':ref(name+'Target')}]
        if name in ('Api','Clamav'):properties['ServiceRegistries']=[{'RegistryArn':get(name+'Discovery','Arn')}]
        depends=['PrivateDefault']
        if name in ('Api','Web'):depends+=['Https','ApiRoute']
        if name in ('Worker','Web'):depends+=['ApiService','ClamavService']
        add(name+'Service','ECS::Service',properties,DependsOn=depends)
    add('DeadLetterAlarm','CloudWatch::Alarm',{'AlarmDescription':'Storage notifications exhausted retries; investigate DLQ','Namespace':'AWS/SQS','MetricName':'ApproximateNumberOfMessagesVisible','Dimensions':[{'Name':'QueueName','Value':get('EventDeadLetter','QueueName')}],'Statistic':'Maximum','Period':60,'EvaluationPeriods':1,'Threshold':0,'ComparisonOperator':'GreaterThanThreshold','TreatMissingData':'notBreaching'})
    outputs={'Url':{'Value':sub('https://${DomainName}')},'LoadBalancerDns':{'Value':get('Balancer','DNSName')},'Bucket':{'Value':ref('Files')},'KmsKeyArn':{'Value':get('StorageKey','Arn')},'StorageQueueUrl':{'Value':ref('StorageEvents')},'Cluster':{'Value':ref('Cluster')}}
    return {'AWSTemplateFormatVersion':'2010-09-09','Description':'Prooflane research deployment. Creates billable AWS infrastructure; review and approve before deploying. Single NAT/database/scanner, no HA claim.', 'Parameters':params,'Conditions':{'HasClaude':{'Fn::Not':[{'Fn::Equals':[ref('AnthropicSecretArn'),'']}]},'HasWorkerImage':{'Fn::Not':[{'Fn::Equals':[ref('WorkerImage'),'']}] }},'Resources':R,'Outputs':outputs}

if __name__=='__main__':
    out=Path(__file__).with_name('template.json')
    template=generate();out.write_text(json.dumps(template,separators=(',',':'))+'\n')
    repositories={'AWSTemplateFormatVersion':'2010-09-09','Description':'Prooflane ECR image repositories; review before creating AWS resources.','Parameters':{'ProjectName':{'Type':'String','Default':'prooflane','AllowedPattern':'[a-z][a-z0-9-]{2,23}'}},'Resources':{},'Outputs':{}}
    for name in ['api','web','research']:
        identifier=name.title()+'Repository'
        repositories['Resources'][identifier]={'Type':'AWS::ECR::Repository','DeletionPolicy':'Retain','UpdateReplacePolicy':'Retain','Properties':{'RepositoryName':sub('${ProjectName}/'+name),'ImageTagMutability':'IMMUTABLE','ImageScanningConfiguration':{'ScanOnPush':True},'EncryptionConfiguration':{'EncryptionType':'AES256'}}}
        repositories['Outputs'][name.title()+'Uri']={'Value':get(identifier,'RepositoryUri')}
    out.with_name('repositories.json').write_text(json.dumps(repositories,separators=(',',':'))+'\n')
    print(f'{len(template["Resources"])} runtime resources; {out.stat().st_size} bytes; no AWS API calls made')
