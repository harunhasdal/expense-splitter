#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { ApplicationStack } from '../lib/application-stack';
import { FrontendStack } from '../lib/frontend-stack';
import { CognitoStack } from '../lib/cognito-stack';

const app = new cdk.App();
const envName = app.node.tryGetContext('env') ?? 'prod';
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'eu-west-1' };

// Required context values — pass with: cdk deploy -c env=dev -c appBaseUrl=https://...
// -c googleClientId=... -c googleClientSecretArn=arn:aws:secretsmanager:...
const appBaseUrl: string = app.node.tryGetContext('appBaseUrl') ?? 'https://REPLACE_ME';
const googleClientId: string = app.node.tryGetContext('googleClientId') ?? 'REPLACE_ME';
const googleClientSecretArn: string = app.node.tryGetContext('googleClientSecretArn') ?? 'REPLACE_ME';

const network = new NetworkStack(app, `NetworkStack-${envName}`, { env, envName });

const cognito = new CognitoStack(app, `CognitoStack-${envName}`, {
  env,
  envName,
  appBaseUrl,
  googleClientId,
  googleClientSecretArn,
});

new ApplicationStack(app, `ApplicationStack-${envName}`, {
  env,
  envName,
  vpc: network.vpc,
  albSg: network.albSg,
  ecsSg: network.ecsSg,
  rdsSg: network.rdsSg,
});

new FrontendStack(app, `FrontendStack-${envName}`, { env, envName });
