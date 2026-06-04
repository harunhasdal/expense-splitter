#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { ApplicationStack } from '../lib/application-stack';
import { FrontendStack } from '../lib/frontend-stack';

const app = new cdk.App();
const envName = app.node.tryGetContext('env') ?? 'prod';
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'eu-west-1' };

const network = new NetworkStack(app, `NetworkStack-${envName}`, { env, envName });

new ApplicationStack(app, `ApplicationStack-${envName}`, {
  env,
  envName,
  vpc: network.vpc,
  albSg: network.albSg,
  ecsSg: network.ecsSg,
  rdsSg: network.rdsSg,
});

new FrontendStack(app, `FrontendStack-${envName}`, { env, envName });
