import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface ApplicationStackProps extends cdk.StackProps {
  envName: string;
  vpc: ec2.Vpc;
  albSg: ec2.SecurityGroup;
  ecsSg: ec2.SecurityGroup;
  rdsSg: ec2.SecurityGroup;
}

export class ApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);
    const isProd = props.envName === 'prod';

    // CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: `/ecs/expense-splitter-api-${props.envName}`,
      retention: isProd ? logs.RetentionDays.THREE_MONTHS : logs.RetentionDays.TWO_WEEKS,
    });

    // RDS PostgreSQL
    new rds.DatabaseInstance(this, 'Database', {
      engine: rds.DatabaseInstanceEngine.postgres({ version: rds.PostgresEngineVersion.VER_16 }),
      instanceType: isProd ? ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL)
                           : ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [props.rdsSg],
      multiAz: isProd,
      storageEncrypted: true,
      deletionProtection: isProd,
      backupRetention: isProd ? cdk.Duration.days(7) : cdk.Duration.days(1),
      parameters: { force_ssl: '1' },
    });

    // ECS Cluster + Service (simplified — full task definition wired during deploy)
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc: props.vpc,
      clusterName: `expense-splitter-${props.envName}`,
    });

    // ALB
    const alb = new elbv2.ApplicationLoadBalancer(this, 'Alb', {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: props.albSg,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
    });

    new cdk.CfnOutput(this, 'AlbDns', { value: alb.loadBalancerDnsName });
  }
}
