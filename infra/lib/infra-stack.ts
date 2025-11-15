import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53targets from 'aws-cdk-lib/aws-route53-targets';
import * as dotenv from 'dotenv';
dotenv.config();

export interface DaveVictorVincentAIVideoGenerationStackProps extends cdk.StackProps {
  hostedZoneId: string;
}

export class DaveVictorVincentAIVideoGenerationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: DaveVictorVincentAIVideoGenerationStackProps) {
    super(scope, id, props);

    // Stage 1: S3 Bucket for video storage
    const videoBucket = new s3.Bucket(this, 'VideoStorageBucket', {
      bucketName: `aivideo-outputs-${this.account}`,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      cors: [
        {
          allowedOrigins: ['*'],
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedHeaders: ['*'],
          exposedHeaders: ['ETag'],
          maxAge: 3000,
        },
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Keep bucket on stack deletion
    });

    // Export bucket name for use in other stages
    new cdk.CfnOutput(this, 'VideoBucketName', {
      value: videoBucket.bucketName,
      exportName: 'VideoBucketName',
    });

    // Stage 2: Aurora Postgres
    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
      isDefault: true,
    });

    // Security group for Aurora (will allow ECS access in Stage 3)
    const auroraSecurityGroup = new ec2.SecurityGroup(this, 'AuroraSecurityGroup', {
      vpc,
      description: 'Security group for Aurora Postgres',
      allowAllOutbound: true,
    });

    // Security group for ECS (created here so Aurora can reference it)
    const ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true,
    });

    // Allow ECS to connect to Aurora on port 5432
    auroraSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from ECS'
    );

    // Load DB credentials from .env
    const dbUsername = process.env.DB_USERNAME || 'aivideo';
    const dbPassword = process.env.DB_PASSWORD;

    if (!dbPassword) {
      throw new Error("DB_PASSWORD must be set in your .env file");
    }

    // Create Aurora Serverless v2 cluster
    const auroraCluster = new rds.DatabaseCluster(this, 'AuroraCluster', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_17_5,
      }),
      credentials: rds.Credentials.fromUsername(dbUsername, {
        password: cdk.SecretValue.unsafePlainText(dbPassword),
      }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 1,
      defaultDatabaseName: 'videogen',
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      securityGroups: [auroraSecurityGroup],
      writer: rds.ClusterInstance.serverlessV2('writer'),
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Export values for use in other stages
    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      exportName: 'VpcId',
    });

    new cdk.CfnOutput(this, 'ECSSecurityGroupId', {
      value: ecsSecurityGroup.securityGroupId,
      exportName: 'ECSSecurityGroupId',
    });


    new cdk.CfnOutput(this, 'AuroraClusterEndpoint', {
      value: auroraCluster.clusterEndpoint.hostname,
      exportName: 'AuroraClusterEndpoint',
    });

    // Stage 3: ECS Cluster & Services
    // Create ECS Fargate cluster
    const cluster = new ecs.Cluster(this, 'AIVideoCluster', {
      vpc,
      clusterName: 'aivideo-cluster',
    });

    // Create CloudWatch log group
    const logGroup = new logs.LogGroup(this, 'ECSLogGroup', {
      logGroupName: '/ecs/aivideo',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Task execution role with required permissions
    const taskExecutionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Grant permissions for ECR and S3
    taskExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ecr:GetAuthorizationToken',
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
        ],
        resources: ['*'],
      })
    );

    videoBucket.grantReadWrite(taskExecutionRole);

    // Security group for Redis
    const redisSecurityGroup = new ec2.SecurityGroup(this, 'RedisSecurityGroup', {
      vpc,
      description: 'Security group for Redis',
      allowAllOutbound: true,
    });

    // Allow ECS to connect to Redis on port 6379
    redisSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(6379),
      'Allow Redis access from ECS'
    );

    // Service discovery namespace
    const namespace = cluster.addDefaultCloudMapNamespace({
      name: 'aivideo.local',
    });

    // Redis Service
    const redisTaskDefinition = new ecs.FargateTaskDefinition(this, 'RedisTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole: taskExecutionRole,
    });

    redisTaskDefinition.addContainer('RedisContainer', {
      image: ecs.ContainerImage.fromRegistry('redis:7-alpine'),
      memoryLimitMiB: 512,
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'redis',
        logGroup,
      }),
      portMappings: [
        {
          containerPort: 6379,
          protocol: ecs.Protocol.TCP,
        },
      ],
      healthCheck: {
        command: ['CMD-SHELL', 'redis-cli ping || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    const redisService = new ecs.FargateService(this, 'RedisService', {
      cluster,
      taskDefinition: redisTaskDefinition,
      desiredCount: 1,
      securityGroups: [redisSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      assignPublicIp: true,
      cloudMapOptions: {
        name: 'redis',
        cloudMapNamespace: namespace,
      },
    });

    // API Service
    // Get image URI from environment variable (set by GitHub Actions)
    const imageUri = process.env.IMAGE_URI || `971422717446.dkr.ecr.us-east-1.amazonaws.com/aivideo/backend:latest`;

    const apiTaskDefinition = new ecs.FargateTaskDefinition(this, 'APITaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole: taskExecutionRole,
    });

    const apiContainer = apiTaskDefinition.addContainer('APIContainer', {
      image: ecs.ContainerImage.fromRegistry(imageUri),
      memoryLimitMiB: 512,
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'api',
        logGroup,
      }),
      environment: {
        REDIS_URL: 'redis://redis.aivideo.local:6379/0',
        S3_BUCKET: videoBucket.bucketName,
        AWS_REGION: this.region,
        AURORA_ENDPOINT: auroraCluster.clusterEndpoint.hostname,
        AURORA_PORT: auroraCluster.clusterEndpoint.port.toString(),
        AURORA_DB_NAME: 'videogen',
        DATABASE_USERNAME: dbUsername,
        DATABASE_PASSWORD: dbPassword,
      },
      portMappings: [
        {
          containerPort: 8000,
          protocol: ecs.Protocol.TCP,
        },
      ],
      healthCheck: {
        command: ['CMD-SHELL', 'python -c "import urllib.request; urllib.request.urlopen(\'http://localhost:8000/health\').close()" || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10),
        retries: 3,
        startPeriod: cdk.Duration.seconds(120),
      },
    });

    const apiService = new ecs.FargateService(this, 'APIService', {
      cluster,
      taskDefinition: apiTaskDefinition,
      desiredCount: 1,
      securityGroups: [ecsSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      assignPublicIp: true,
      enableExecuteCommand: true,
    });

    // Ensure Redis is ready before starting API
    apiService.node.addDependency(redisService);

    // Worker Service
    const workerTaskDefinition = new ecs.FargateTaskDefinition(this, 'WorkerTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole: taskExecutionRole,
    });

    const workerContainer = workerTaskDefinition.addContainer('WorkerContainer', {
      image: ecs.ContainerImage.fromRegistry(imageUri),
      memoryLimitMiB: 512,
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'worker',
        logGroup,
      }),

      command: [
        'celery',
        '-A',
        'app.orchestrator.celery_app',
        'worker',
        '--loglevel=info',
        '--concurrency=4',
      ],

      // MERGED environment block (only one allowed)
      environment: {
        REDIS_URL: 'redis://redis.aivideo.local:6379/0',
        S3_BUCKET: videoBucket.bucketName,
        AWS_REGION: this.region,
        AURORA_ENDPOINT: auroraCluster.clusterEndpoint.hostname,
        AURORA_PORT: auroraCluster.clusterEndpoint.port.toString(),
        AURORA_DB_NAME: 'videogen',

        DATABASE_USERNAME: dbUsername,
        DATABASE_PASSWORD: dbPassword,
      },

      healthCheck: {
        command: [
          'CMD-SHELL',
          'celery -A app.orchestrator.celery_app inspect ping || exit 1'
        ],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10),
        retries: 3,
        startPeriod: cdk.Duration.seconds(120),
      },
    });

    const workerService = new ecs.FargateService(this, 'WorkerService', {
      cluster,
      taskDefinition: workerTaskDefinition,
      desiredCount: 1,
      securityGroups: [ecsSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      assignPublicIp: true,
      enableExecuteCommand: true,
    });

    // Ensure Redis is ready before starting Worker
    workerService.node.addDependency(redisService);

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      exportName: 'ClusterName',
    });

    new cdk.CfnOutput(this, 'APIServiceName', {
      value: apiService.serviceName,
      exportName: 'APIServiceName',
    });

    // Stage 4: Application Load Balancer
    // Security group for ALB
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc,
      description: 'Security group for Application Load Balancer',
      allowAllOutbound: true,
    });

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP from internet'
    );

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS from internet'
    );

    // Allow ALB to connect to ECS
    ecsSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow ALB to connect to API service'
    );

    // Create ALB
    const alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });

    // Target group for API service
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'APITargetGroup', {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // Attach API service to target group
    apiService.attachToApplicationTargetGroup(targetGroup);

    // HTTP listener (temporary, HTTPS will be added in Stage 6)
    alb.addListener('HTTPListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [targetGroup],
    });

    new cdk.CfnOutput(this, 'ALBDNSName', {
      value: alb.loadBalancerDnsName,
      exportName: 'ALBDNSName',
    });

    // Stage 5: ACM Certificate
    // Create hosted zone reference (reused in Stage 6)
    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'HostedZone', {
      hostedZoneId: props.hostedZoneId,
      zoneName: 'gauntlet3.com',
    });

    const certificate = new acm.Certificate(this, 'Certificate', {
      domainName: 'aivideo-api.gauntlet3.com',
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    new cdk.CfnOutput(this, 'CertificateArn', {
      value: certificate.certificateArn,
      exportName: 'CertificateArn',
    });

    // Stage 6: Route53 & HTTPS
    // Add HTTPS listener
    const httpsListener = alb.addListener('HTTPSListener', {
      port: 443,
      protocol: elbv2.ApplicationProtocol.HTTPS,
      certificates: [certificate],
      defaultTargetGroups: [targetGroup],
    });

    // Note: The HTTP listener added in Stage 4 will remain
    // In production, you may want to remove it and only use HTTPS
    // For now, both HTTP and HTTPS will work

    new route53.ARecord(this, 'APIRecord', {
      zone: hostedZone,
      recordName: 'aivideo-api',
      target: route53.RecordTarget.fromAlias(
        new route53targets.LoadBalancerTarget(alb)
      ),
    });

    new cdk.CfnOutput(this, 'APIURL', {
      value: `https://aivideo-api.gauntlet3.com`,
      description: 'API endpoint URL',
    });
  }
}
