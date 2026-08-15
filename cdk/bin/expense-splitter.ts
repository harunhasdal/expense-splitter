#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { EcrStack } from '../lib/ecr-stack';
import { ApplicationStack } from '../lib/application-stack';
import { FrontendStack } from '../lib/frontend-stack';
import { CognitoStack } from '../lib/cognito-stack';

const app = new cdk.App();
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'eu-west-1' };

// Baseline image tag for the CDK-managed task definition. Steady-state
// rollouts register new revisions at :<sha> from CI (see deploy.yml).
const imageTag: string = app.node.tryGetContext('imageTag') ?? 'bootstrap';

// Google federation is off by default so we can deploy before Google OAuth
// credentials exist. Enable with `-c enableGoogle=true` once the SSM param
// (google-client-id) and secret (google-client-secret) are in place.
const enableGoogle: boolean = app.node.tryGetContext('enableGoogle') === true
  || app.node.tryGetContext('enableGoogle') === 'true';

// Shared, single ECR repository used by all environments (the image is
// configuration-agnostic — env-specific config is injected at runtime).
new EcrStack(app, 'EcrStack', { env });

for (const envName of ['staging', 'prod']) {
  const network = new NetworkStack(app, `NetworkStack-${envName}`, { env, envName });

  const cognito = new CognitoStack(app, `CognitoStack-${envName}`, { env, envName, enableGoogle });

  new ApplicationStack(app, `ApplicationStack-${envName}`, {
    env,
    envName,
    vpc: network.vpc,
    ecsSg: network.ecsSg,
    rdsSg: network.rdsSg,
    cognitoRegion: env.region,
    cognitoUserPoolId: cognito.userPoolId,
    cognitoClientId: cognito.userPoolClientId,
    cognitoDomain: cognito.cognitoDomain,
    imageTag,
  });

  new FrontendStack(app, `FrontendStack-${envName}`, { env, envName });
}
