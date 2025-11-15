#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DaveVictorVincentAIVideoGenerationStack } from '../lib/infra-stack';

const app = new cdk.App();
new DaveVictorVincentAIVideoGenerationStack(app, 'DaveVictorVincentAIVideoGenerationStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
    region: 'us-east-1',
  },
  hostedZoneId: 'Z02772533IJIPQUFR1DYJ',
});
