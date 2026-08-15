import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';

/**
 * A single ECR repository shared across all environments.
 *
 * The API image is configuration-agnostic (all env-specific config is injected
 * at runtime via env vars / Secrets Manager), so staging and prod pull the same
 * `expense-splitter-api:<tag>`. Keeping the repo in its own stack lets us push an
 * initial image before the Express service is created (which needs a valid image
 * to reach a stable state).
 */
export class EcrStack extends cdk.Stack {
  readonly repository: ecr.Repository;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.repository = new ecr.Repository(this, 'ApiRepo', {
      repositoryName: 'expense-splitter-api',
      imageScanOnPush: true,
      lifecycleRules: [{ maxImageCount: 20 }],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    new cdk.CfnOutput(this, 'RepositoryUri', { value: this.repository.repositoryUri });
  }
}
