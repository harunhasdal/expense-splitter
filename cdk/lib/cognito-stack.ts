import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface CognitoStackProps extends cdk.StackProps {
  envName: string;
  appBaseUrl: string;       // e.g. "https://api.expense-splitter.example.com"
  googleClientId: string;   // Google OAuth2 client ID (from Secrets Manager in practice)
  googleClientSecretArn: string;  // ARN of secret holding Google client secret
}

export class CognitoStack extends cdk.Stack {
  readonly userPoolId: string;
  readonly userPoolClientId: string;
  readonly cognitoDomain: string;

  constructor(scope: Construct, id: string, props: CognitoStackProps) {
    super(scope, id, props);

    const domainPrefix = `expense-splitter-${props.envName}`;

    // User Pool — email sign-in + Google federation
    const userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `expense-splitter-${props.envName}`,
      selfSignUpEnabled: false,         // invites only / federated only
      signInAliases: { email: true },
      autoVerify: { email: true },
      standardAttributes: {
        email: { required: true, mutable: true },
        fullname: { required: false, mutable: true },
        profilePicture: { required: false, mutable: true },
      },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: props.envName === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
    });

    // Google IdP
    const googleSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this, 'GoogleSecret', props.googleClientSecretArn
    );
    const googleIdp = new cognito.UserPoolIdentityProviderGoogle(this, 'Google', {
      userPool,
      clientId: props.googleClientId,
      clientSecretValue: googleSecret.secretValue,
      scopes: ['openid', 'email', 'profile'],
      attributeMapping: {
        email: cognito.ProviderAttribute.GOOGLE_EMAIL,
        fullname: cognito.ProviderAttribute.GOOGLE_NAME,
        profilePicture: cognito.ProviderAttribute.GOOGLE_PICTURE,
      },
    });

    // App Client — authorization code flow with PKCE + client secret
    const client = new cognito.UserPoolClient(this, 'AppClient', {
      userPool,
      userPoolClientName: `expense-splitter-api-${props.envName}`,
      generateSecret: true,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          `${props.appBaseUrl}/auth/callback`,
          'http://localhost:8000/auth/callback',  // local dev
        ],
        logoutUrls: [
          `${props.appBaseUrl}/auth/logout-callback`,
          'http://localhost:8000/auth/logout-callback',
        ],
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
        cognito.UserPoolClientIdentityProvider.GOOGLE,
      ],
      idTokenValidity: cdk.Duration.hours(24),
      accessTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      preventUserExistenceErrors: true,
    });
    client.node.addDependency(googleIdp);

    // Cognito Managed Login domain
    new cognito.UserPoolDomain(this, 'Domain', {
      userPool,
      cognitoDomain: { domainPrefix },
    });

    this.userPoolId = userPool.userPoolId;
    this.userPoolClientId = client.userPoolClientId;
    this.cognitoDomain = domainPrefix;

    new cdk.CfnOutput(this, 'UserPoolId', { value: userPool.userPoolId });
    new cdk.CfnOutput(this, 'UserPoolClientId', { value: client.userPoolClientId });
    new cdk.CfnOutput(this, 'CognitoDomain', {
      value: `${domainPrefix}.auth.${this.region}.amazoncognito.com`,
    });
    new cdk.CfnOutput(this, 'ManagedLoginUrl', {
      value: `https://${domainPrefix}.auth.${this.region}.amazoncognito.com/login`,
    });
  }
}
