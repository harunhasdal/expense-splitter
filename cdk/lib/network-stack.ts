import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

interface NetworkStackProps extends cdk.StackProps {
  envName: string;
}

export class NetworkStack extends cdk.Stack {
  readonly vpc: ec2.Vpc;
  readonly ecsSg: ec2.SecurityGroup;
  readonly rdsSg: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'VPC', {
      ipAddresses: ec2.IpAddresses.cidr(props.envName === 'prod' ? '10.0.0.0/16' : '10.1.0.0/16'),
      maxAzs: 2,
      natGateways: props.envName === 'prod' ? 2 : 1,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
      ],
    });

    // ECS task security group. Express Mode creates and manages the ALB (and its
    // own SG); it places the load balancer in this VPC. We allow the task port
    // (8000) from the VPC CIDR so the Express-managed ALB can reach the tasks,
    // while the public internet only ever reaches the ALB on 443 (HTTPS).
    this.ecsSg = new ec2.SecurityGroup(this, 'EcsSg', { vpc: this.vpc, description: 'ECS task SG' });
    this.ecsSg.addIngressRule(
      ec2.Peer.ipv4(this.vpc.vpcCidrBlock),
      ec2.Port.tcp(8000),
      'App port from in-VPC ALB (Express Mode)'
    );

    // RDS is reachable only from the ECS tasks.
    this.rdsSg = new ec2.SecurityGroup(this, 'RdsSg', { vpc: this.vpc, description: 'RDS SG' });
    this.rdsSg.addIngressRule(this.ecsSg, ec2.Port.tcp(5432), 'PostgreSQL from ECS tasks');

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId, exportName: `${id}-VpcId` });
  }
}
