import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

interface NetworkStackProps extends cdk.StackProps {
  envName: string;
}

export class NetworkStack extends cdk.Stack {
  readonly vpc: ec2.Vpc;
  readonly albSg: ec2.SecurityGroup;
  readonly ecsSg: ec2.SecurityGroup;
  readonly rdsSg: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'VPC', {
      cidr: props.envName === 'prod' ? '10.0.0.0/16' : '10.1.0.0/16',
      maxAzs: 2,
      natGateways: props.envName === 'prod' ? 2 : 1,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
      ],
    });

    this.albSg = new ec2.SecurityGroup(this, 'AlbSg', { vpc: this.vpc, description: 'ALB SG' });
    this.albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'HTTPS from internet');
    this.albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'HTTP redirect');

    this.ecsSg = new ec2.SecurityGroup(this, 'EcsSg', { vpc: this.vpc, description: 'ECS SG' });
    this.ecsSg.addIngressRule(this.albSg, ec2.Port.tcp(8000), 'From ALB');

    this.rdsSg = new ec2.SecurityGroup(this, 'RdsSg', { vpc: this.vpc, description: 'RDS SG' });
    this.rdsSg.addIngressRule(this.ecsSg, ec2.Port.tcp(5432), 'From ECS');

    // Stack outputs for cross-stack referencing
    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId, exportName: `${id}-VpcId` });
  }
}
