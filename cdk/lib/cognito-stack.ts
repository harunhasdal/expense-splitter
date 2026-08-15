import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface CognitoStackProps extends cdk.StackProps {
  envName: string;
  // When false, the Google IdP is not provisioned and the app client offers
  // Cognito (email/password) sign-in only. Lets us deploy before Google OAuth
  // credentials exist; flip on (with google-client-id SSM + google-client-secret
  // secret in place) to add federation later. Controlled by `-c enableGoogle=true`.
  enableGoogle: boolean;
}

export class CognitoStack extends cdk.Stack {
  readonly userPoolId: string;
  readonly userPoolClientId: string;
  readonly cognitoDomain: string;

  constructor(scope: Construct, id: string, props: CognitoStackProps) {
    super(scope, id, props);

    const domainPrefix = `expense-splitter-${props.envName}`;

    // Config source (§8): non-secrets from SSM Parameter Store, the Google
    // client secret from Secrets Manager. `api-base-url` is the two-phase seam
    // (placeholder in phase 1, real Express domain in phase 2). All resolve at
    // deploy time, so re-running phase 2 after the SSM update refreshes the
    // callback URLs.
    const appBaseUrl = ssm.StringParameter.valueForStringParameter(
      this, `/expense-splitter/${props.envName}/api-base-url`
    );

    // User Pool — email sign-in (+ optional Google federation, see enableGoogle)
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

    // Google IdP — provisioned only when enabled (needs google-client-id in SSM
    // and the google-client-secret in Secrets Manager).
    let googleIdp: cognito.UserPoolIdentityProviderGoogle | undefined;
    if (props.enableGoogle) {
      const googleClientId = ssm.StringParameter.valueForStringParameter(
        this, `/expense-splitter/${props.envName}/google-client-id`
      );
      const googleSecret = secretsmanager.Secret.fromSecretNameV2(
        this, 'GoogleSecret', `expense-splitter/${props.envName}/google-client-secret`
      );
      googleIdp = new cognito.UserPoolIdentityProviderGoogle(this, 'Google', {
        userPool,
        clientId: googleClientId,
        clientSecretValue: googleSecret.secretValue,
        scopes: ['openid', 'email', 'profile'],
        attributeMapping: {
          email: cognito.ProviderAttribute.GOOGLE_EMAIL,
          fullname: cognito.ProviderAttribute.GOOGLE_NAME,
          profilePicture: cognito.ProviderAttribute.GOOGLE_PICTURE,
        },
      });
    }

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
          `${appBaseUrl}/auth/callback`,
          'http://localhost:8000/auth/callback',  // local dev
        ],
        logoutUrls: [
          `${appBaseUrl}/auth/logout-callback`,
          'http://localhost:8000/auth/logout-callback',
        ],
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
        ...(props.enableGoogle ? [cognito.UserPoolClientIdentityProvider.GOOGLE] : []),
      ],
      idTokenValidity: cdk.Duration.hours(24),
      accessTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      preventUserExistenceErrors: true,
    });
    // Ensure the IdP exists before the client references it.
    if (googleIdp) {
      client.node.addDependency(googleIdp);
    }

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
