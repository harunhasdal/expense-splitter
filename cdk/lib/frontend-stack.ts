import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

interface FrontendStackProps extends cdk.StackProps {
  envName: string;
}

export class FrontendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `expense-splitter-frontend-${props.envName}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const oai = new cloudfront.OriginAccessIdentity(this, 'OAI');
    bucket.grantRead(oai);

    const securityHeadersPolicy = new cloudfront.ResponseHeadersPolicy(this, 'SecurityHeaders', {
      securityHeadersBehavior: {
        contentSecurityPolicy: {
          contentSecurityPolicy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'",
          override: true,
        },
        strictTransportSecurity: {
          accessControlMaxAge: cdk.Duration.days(365),
          includeSubdomains: true,
          override: true,
        },
        contentTypeOptions: { override: true },
        frameOptions: { frameOption: cloudfront.HeadersFrameOption.DENY, override: true },
        referrerPolicy: {
          referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
          override: true,
        },
      },
    });

    // ---- Backend origin (ECS Express Mode) — reverse proxy ----
    // Single-origin model: the SPA and the API are both served from THIS
    // distribution. The SPA calls the API with same-origin relative paths
    // (/auth, /groups, /health) — required because the session/CSRF cookies are
    // SameSite=Lax (browsers won't send them cross-site) and the CSP is
    // connect-src 'self'. The backend's raw AWS-provided hostname (no scheme)
    // comes from SSM, written at bootstrap alongside the api-base-url seam.
    const apiOriginDomain = ssm.StringParameter.valueForStringParameter(
      this, `/expense-splitter/${props.envName}/api-origin-domain`
    );
    const backendOrigin = new origins.HttpOrigin(apiOriginDomain, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
    });

    // API behavior: never cache, and forward everything (cookies, auth headers,
    // query string) to the backend. ALL_VIEWER_EXCEPT_HOST_HEADER sends Host =
    // the origin's own domain so the Express ALB's TLS/SNI + routing match; the
    // app's public URL is carried to the backend separately via APP_BASE_URL.
    const apiBehavior: cloudfront.BehaviorOptions = {
      origin: backendOrigin,
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
      cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
      originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
    };

    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(bucket, { originAccessIdentity: oai }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy: securityHeadersPolicy,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
      },
      // Route the API surface to the backend; everything else falls through to
      // the S3-hosted SPA (with the SPA 403/404 -> index.html fallback below).
      additionalBehaviors: {
        '/auth/*': apiBehavior,
        '/groups': apiBehavior,
        '/groups/*': apiBehavior,
        '/health': apiBehavior,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html' },
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html' },
      ],
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });

    new cdk.CfnOutput(this, 'DistributionId', { value: distribution.distributionId });
    new cdk.CfnOutput(this, 'DistributionDomain', { value: distribution.distributionDomainName });
  }
}
