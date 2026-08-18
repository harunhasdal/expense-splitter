import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface ApplicationStackProps extends cdk.StackProps {
  envName: string;
  vpc: ec2.Vpc;
  ecsSg: ec2.SecurityGroup;
  rdsSg: ec2.SecurityGroup;
  // Cognito wiring (from CognitoStack)
  cognitoRegion: string;
  cognitoUserPoolId: string;
  cognitoClientId: string;
  cognitoDomain: string;
  // Image tag deployed by CDK for the baseline task definition. Steady-state
  // rollouts register new revisions at :<sha> from CI (see deploy.yml).
  imageTag?: string;
}

/**
 * Backend compute, built around Amazon ECS Express Mode
 * (`AWS::ECS::ExpressGatewayService`). Express Mode provisions and manages the
 * internet-facing ALB, HTTPS listener + ACM certificate, target group, the
 * Fargate service, target-tracking auto-scaling, and deploy alarms. We own the
 * task definition, RDS, secrets, log group, and IAM roles.
 */
export class ApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);
    const isProd = props.envName === 'prod';
    const imageTag = props.imageTag ?? 'bootstrap';

    // Bootstrap seam: the Express service's `/health` check hits the DB, and its
    // secrets must be valid JSON pointing at a reachable RDS — neither is true on
    // the first deploy (empty secret shell; RDS is in this same stack and Express
    // does not depend on it). So bootstrap runs `-c deployExpress=false` to create
    // RDS + secret + task def, populates the secret out-of-band, then redeploys
    // with the flag defaulting true to add the service (which now stabilizes).
    const deployExpress = this.node.tryGetContext('deployExpress') !== 'false'
      && this.node.tryGetContext('deployExpress') !== false;

    // ---- Shared ECR repository (created once in EcrStack) ----
    const repo = ecr.Repository.fromRepositoryName(this, 'ApiRepo', 'expense-splitter-api');

    // ---- CloudWatch log group ----
    // With a bring-your-own task definition, Express Mode does NOT create the
    // log group; we must own it (or grant the execution role permission to
    // create it). We create it explicitly and point the container's awslogs at it.
    const logGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: `/ecs/expense-splitter-api-${props.envName}`,
      retention: isProd ? logs.RetentionDays.THREE_MONTHS : logs.RetentionDays.TWO_WEEKS,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // ---- RDS PostgreSQL ----
    new rds.DatabaseInstance(this, 'Database', {
      engine: rds.DatabaseInstanceEngine.postgres({ version: rds.PostgresEngineVersion.VER_16 }),
      instanceType: isProd
        ? ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL)
        : ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [props.rdsSg],
      databaseName: 'expense_splitter',
      multiAz: isProd,
      storageEncrypted: true,
      deletionProtection: isProd,
      backupRetention: isProd ? cdk.Duration.days(7) : cdk.Duration.days(1),
      removalPolicy: isProd ? cdk.RemovalPolicy.SNAPSHOT : cdk.RemovalPolicy.DESTROY,
      parameters: { 'rds.force_ssl': '1' },
    });

    // ---- Application secret shell ----
    // Contents are populated out-of-band during bootstrap (see runbook): keys
    // `database_url` (assembled from the RDS-generated secret + endpoint),
    // `cognito_client_secret` (from the Cognito app client), and
    // `csrf_secret_key`. CDK only owns the shell; put-secret-value is not
    // reverted on subsequent deploys.
    const apiSecret = new secretsmanager.Secret(this, 'ApiSecret', {
      secretName: `expense-splitter/${props.envName}/api`,
      description: 'DATABASE_URL, COGNITO_CLIENT_SECRET, CSRF_SECRET_KEY (populated at bootstrap)',
    });

    // ---- IAM roles ----
    // Execution role: pull image, write logs, read secrets (ECS uses this to
    // resolve `secrets` at task start).
    const executionRole = new iam.Role(this, 'ExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Task role: app runtime AWS calls (minimal for now).
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // Infrastructure role: lets Express Mode manage the ALB / target group /
    // scaling / alarms on our behalf.
    const infraRole = new iam.Role(this, 'InfraRole', {
      assumedBy: new iam.ServicePrincipal('ecs.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonECSInfrastructureRoleforExpressGatewayServices'
        ),
      ],
    });

    // ---- Config from SSM (written during bootstrap / phase 2) ----
    // api-base-url is the app's PUBLIC base URL. Under the CloudFront
    // reverse-proxy model this is the CloudFront domain (the single origin that
    // serves the SPA and proxies the API), NOT the backend Express domain — the
    // browser only ever sees CloudFront. APP_BASE_URL builds OAuth redirect_uris
    // (/auth/callback), so it must point where the browser lands. Seeded with a
    // placeholder in phase 1, set to the CloudFront domain in phase 2.
    const appBaseUrl = ssm.StringParameter.valueForStringParameter(
      this, `/expense-splitter/${props.envName}/api-base-url`
    );
    const allowedOrigins = ssm.StringParameter.valueForStringParameter(
      this, `/expense-splitter/${props.envName}/allowed-origins`
    );

    // ---- ECS cluster (Fargate) ----
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc: props.vpc,
      clusterName: `expense-splitter-${props.envName}`,
      enableFargateCapacityProviders: true,
    });

    // ---- Custom Fargate task definition ----
    // Express Mode BYO-task-def requirements: a container named `Main` with a
    // single named TCP port mapping, Fargate-compatible. Express derives
    // cpu/memory/roles from this task def, so we do NOT repeat them on the
    // Express resource.
    const taskDef = new ecs.FargateTaskDefinition(this, 'ApiTaskDef', {
      family: `expense-splitter-api-${props.envName}`,
      cpu: 1024,
      memoryLimitMiB: 2048,
      executionRole,
      taskRole,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.X86_64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    taskDef.addContainer('Main', {
      image: ecs.ContainerImage.fromEcrRepository(repo, imageTag),
      portMappings: [{ containerPort: 8000, name: 'web', protocol: ecs.Protocol.TCP }],
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'api', logGroup }),
      environment: {
        COGNITO_REGION: props.cognitoRegion,
        COGNITO_USER_POOL_ID: props.cognitoUserPoolId,
        COGNITO_CLIENT_ID: props.cognitoClientId,
        COGNITO_DOMAIN: props.cognitoDomain,
        JWT_EXPIRY_SECONDS: '86400',
        ALLOWED_ORIGINS: allowedOrigins,
        APP_BASE_URL: appBaseUrl,
        LOG_LEVEL: 'INFO',
        DISABLE_DOCS: isProd ? 'true' : 'false',
      },
      secrets: {
        DATABASE_URL: ecs.Secret.fromSecretsManager(apiSecret, 'database_url'),
        COGNITO_CLIENT_SECRET: ecs.Secret.fromSecretsManager(apiSecret, 'cognito_client_secret'),
        CSRF_SECRET_KEY: ecs.Secret.fromSecretsManager(apiSecret, 'csrf_secret_key'),
      },
    });

    // ---- Express Mode service ----
    // aws-cdk-lib 2.147 predates AWS::ECS::ExpressGatewayService, so we use the
    // CfnResource escape hatch with raw (PascalCase) CloudFormation properties.
    // Only InfrastructureRoleArn is required; supplying TaskDefinitionArn means
    // Express uses our task def as-is (image/cpu/mem/roles come from it), so we
    // must NOT set ExecutionRoleArn/TaskRoleArn/Cpu/Memory/PrimaryContainer here.
    // Public subnets => internet-facing ALB + public-IP tasks (accepted, §7).
    if (deployExpress) {
      const express = new cdk.CfnResource(this, 'ApiExpress', {
        type: 'AWS::ECS::ExpressGatewayService',
        properties: {
          ServiceName: `expense-splitter-api-${props.envName}`,
          Cluster: cluster.clusterName,
          InfrastructureRoleArn: infraRole.roleArn,
          TaskDefinitionArn: taskDef.taskDefinitionArn,
          HealthCheckPath: '/health',
          NetworkConfiguration: {
            Subnets: props.vpc.publicSubnets.map((s) => s.subnetId),
            SecurityGroups: [props.ecsSg.securityGroupId],
          },
          ScalingTarget: {
            MinTaskCount: isProd ? 2 : 1,
            MaxTaskCount: isProd ? 6 : 2,
            AutoScalingMetric: 'AVERAGE_CPU',
            AutoScalingTargetValue: 60,
          },
        },
      });

      // Express mints an AWS-provided domain; capture it for the phase-2 seam
      // (write into /expense-splitter/<env>/api-base-url, then redeploy).
      new cdk.CfnOutput(this, 'ApiEndpoint', {
        value: express.getAtt('Endpoint').toString(),
        description: 'AWS-provided Express Mode domain for the API',
      });
    }

    // ---- Outputs ----
    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    // The exact task-def revision this deploy registered — CI runs the DB
    // migration one-off against this ARN (see deploy.yml).
    new cdk.CfnOutput(this, 'TaskDefinitionArn', { value: taskDef.taskDefinitionArn });
    // Network config for the migration `run-task`. Private subnets give NAT
    // egress (ECR pull, Secrets Manager) while `ecsSg` reaches RDS on 5432.
    new cdk.CfnOutput(this, 'MigrationSubnetIds', {
      value: cdk.Fn.join(',', props.vpc.privateSubnets.map((s) => s.subnetId)),
      description: 'Private subnet IDs for the migration run-task',
    });
    new cdk.CfnOutput(this, 'EcsSecurityGroupId', { value: props.ecsSg.securityGroupId });
  }
}
