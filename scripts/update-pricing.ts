#!/usr/bin/env node
/**
 * Pricing Data Update Script
 * 
 * This script helps maintain the pricing.json file with up-to-date
 * Azure OpenAI and Azure Managed Redis pricing.
 * 
 * Usage:
 *   npx ts-node scripts/update-pricing.ts
 *   # or
 *   node scripts/update-pricing.js
 * 
 * Note: Pricing must be manually verified from Azure sources as there's
 * no public API for pricing data. This script provides structure and
 * validation, but actual prices should be verified at:
 * 
 * - Azure OpenAI: https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
 * - Azure Managed Redis: https://azure.microsoft.com/en-us/pricing/details/azure-cache-for-redis/
 * - OpenAI (for comparison): https://openai.com/pricing
 */

import * as fs from 'fs';
import * as path from 'path';

interface PricingUpdate {
  model: string;
  field: string;
  oldValue: number;
  newValue: number;
}

// Current known pricing (January 2026) - UPDATE THESE WHEN PRICES CHANGE
const CURRENT_AZURE_OPENAI_PRICING = {
  'gpt-4o': {
    inputPer1MTokens: 2.50,
    outputPer1MTokens: 10.00,
    cachedInputPer1MTokens: 1.25,
    ptuPerHour: 2.00,
  },
  'gpt-4o-mini': {
    inputPer1MTokens: 0.15,
    outputPer1MTokens: 0.60,
    cachedInputPer1MTokens: 0.075,
    ptuPerHour: 0.22,
  },
  'gpt-4-turbo': {
    inputPer1MTokens: 10.00,
    outputPer1MTokens: 30.00,
    ptuPerHour: 6.00,
  },
  'gpt-35-turbo': {
    inputPer1MTokens: 0.50,
    outputPer1MTokens: 1.50,
  },
  'o1': {
    inputPer1MTokens: 15.00,
    outputPer1MTokens: 60.00,
    cachedInputPer1MTokens: 7.50,
  },
  'o1-mini': {
    inputPer1MTokens: 3.00,
    outputPer1MTokens: 12.00,
    cachedInputPer1MTokens: 1.50,
  },
};

const CURRENT_EMBEDDING_PRICING = {
  'text-embedding-3-large': { per1MTokens: 0.13 },
  'text-embedding-3-small': { per1MTokens: 0.02 },
  'text-embedding-ada-002': { per1MTokens: 0.10 },
};

// Azure Managed Redis pricing (West US 2, monthly estimates)
const CURRENT_AMR_PRICING = {
  memoryOptimized: {
    M10: 438, M20: 876, M50: 2190, M100: 4380,
    M150: 6570, M250: 10950, M350: 15330, M500: 21900,
    M700: 30660, M1000: 43800,
  },
  balanced: {
    B0: 22, B1: 44, B3: 131, B5: 219,
    B10: 438, B20: 876, B50: 2190, B100: 4380,
  },
  computeOptimized: {
    C1: 88, C3: 175, C5: 263, C10: 526, C20: 1052,
  },
  flashOptimized: {
    F300: 5110, F700: 10220, F1500: 18615,
  },
};

function loadPricingData(): any {
  const pricingPath = path.join(__dirname, '../frontend/src/data/pricing.json');
  const data = fs.readFileSync(pricingPath, 'utf-8');
  return JSON.parse(data);
}

function savePricingData(data: any): void {
  const pricingPath = path.join(__dirname, '../frontend/src/data/pricing.json');
  fs.writeFileSync(pricingPath, JSON.stringify(data, null, 2));
  console.log('✅ Pricing data saved to', pricingPath);
}

function validateAndUpdate(): PricingUpdate[] {
  const pricing = loadPricingData();
  const updates: PricingUpdate[] = [];
  
  // Update models
  for (const [modelId, prices] of Object.entries(CURRENT_AZURE_OPENAI_PRICING)) {
    const model = pricing.models[modelId];
    if (!model) {
      console.warn(`⚠️  Model ${modelId} not found in pricing.json`);
      continue;
    }
    
    const payg = model.pricing?.payAsYouGo;
    if (payg) {
      if (payg.inputPer1MTokens !== (prices as any).inputPer1MTokens) {
        updates.push({
          model: modelId,
          field: 'inputPer1MTokens',
          oldValue: payg.inputPer1MTokens,
          newValue: (prices as any).inputPer1MTokens,
        });
        payg.inputPer1MTokens = (prices as any).inputPer1MTokens;
      }
      if (payg.outputPer1MTokens !== (prices as any).outputPer1MTokens) {
        updates.push({
          model: modelId,
          field: 'outputPer1MTokens',
          oldValue: payg.outputPer1MTokens,
          newValue: (prices as any).outputPer1MTokens,
        });
        payg.outputPer1MTokens = (prices as any).outputPer1MTokens;
      }
    }
  }
  
  // Update embeddings
  for (const [embeddingId, prices] of Object.entries(CURRENT_EMBEDDING_PRICING)) {
    const embedding = pricing.embeddings[embeddingId];
    if (!embedding) {
      console.warn(`⚠️  Embedding ${embeddingId} not found in pricing.json`);
      continue;
    }
    
    if (embedding.pricing?.per1MTokens !== prices.per1MTokens) {
      updates.push({
        model: embeddingId,
        field: 'per1MTokens',
        oldValue: embedding.pricing?.per1MTokens,
        newValue: prices.per1MTokens,
      });
      embedding.pricing.per1MTokens = prices.per1MTokens;
    }
  }
  
  // Update timestamp
  pricing.metadata.lastUpdated = new Date().toISOString().split('T')[0];
  
  if (updates.length > 0) {
    savePricingData(pricing);
    console.log('\n📝 Updates applied:');
    updates.forEach(u => {
      console.log(`   ${u.model}.${u.field}: $${u.oldValue} → $${u.newValue}`);
    });
  } else {
    console.log('✅ All prices are up to date');
  }
  
  return updates;
}

function generatePricingReport(): void {
  const pricing = loadPricingData();
  
  console.log('\n═══════════════════════════════════════════════════════════');
  console.log('              AZURE OPENAI PRICING REPORT');
  console.log('═══════════════════════════════════════════════════════════\n');
  
  console.log('LLM Models (Pay-as-you-go):');
  console.log('───────────────────────────────────────────────────────────');
  console.log('Model            │ Input/1M  │ Output/1M │ Cached/1M');
  console.log('───────────────────────────────────────────────────────────');
  
  for (const [id, model] of Object.entries(pricing.models) as any) {
    const payg = model.pricing?.payAsYouGo;
    if (payg) {
      const cached = payg.cachedInputPer1MTokens ? `$${payg.cachedInputPer1MTokens.toFixed(2)}` : 'N/A';
      console.log(
        `${model.name.padEnd(16)} │ $${payg.inputPer1MTokens.toFixed(2).padStart(6)} │ $${payg.outputPer1MTokens.toFixed(2).padStart(7)} │ ${cached}`
      );
    }
  }
  
  console.log('\nEmbedding Models:');
  console.log('───────────────────────────────────────────────────────────');
  
  for (const [id, model] of Object.entries(pricing.embeddings) as any) {
    console.log(`${model.name.padEnd(25)} │ $${model.pricing.per1MTokens.toFixed(2)} / 1M tokens`);
  }
  
  console.log('\n═══════════════════════════════════════════════════════════');
  console.log('              COST COMPARISON (1M Queries)');
  console.log('═══════════════════════════════════════════════════════════\n');
  
  const scenarios = [
    { name: 'No Cache (100% LLM)', hitRate: 0 },
    { name: '50% Cache Hit Rate', hitRate: 0.5 },
    { name: '70% Cache Hit Rate', hitRate: 0.7 },
    { name: '85% Cache Hit Rate', hitRate: 0.85 },
  ];
  
  // Assume 750 input, 500 output tokens per query
  const inputTokens = 750;
  const outputTokens = 500;
  const embeddingTokens = 100;
  
  for (const [id, model] of Object.entries(pricing.models).slice(0, 3) as any) {
    const payg = model.pricing?.payAsYouGo;
    if (!payg) continue;
    
    console.log(`\n${model.name}:`);
    console.log('───────────────────────────────────────────────────────────');
    
    const costPerLLMCall = 
      (inputTokens / 1_000_000) * payg.inputPer1MTokens +
      (outputTokens / 1_000_000) * payg.outputPer1MTokens;
    
    const embeddingCost = (embeddingTokens / 1_000_000) * 0.13; // text-embedding-3-large
    
    scenarios.forEach(s => {
      const llmCalls = 1_000_000 * (1 - s.hitRate);
      const cacheHits = 1_000_000 * s.hitRate;
      const totalCost = (llmCalls * costPerLLMCall) + (cacheHits * embeddingCost);
      console.log(`  ${s.name.padEnd(22)}: $${totalCost.toLocaleString(undefined, {maximumFractionDigits: 0})}`);
    });
  }
  
  console.log('\n───────────────────────────────────────────────────────────');
  console.log(`Last updated: ${pricing.metadata.lastUpdated}`);
  console.log('Sources:');
  console.log(`  - ${pricing.metadata.sources.azureOpenAI}`);
  console.log(`  - ${pricing.metadata.sources.azureManagedRedis}`);
}

// Main
const args = process.argv.slice(2);

if (args.includes('--report')) {
  generatePricingReport();
} else if (args.includes('--validate')) {
  validateAndUpdate();
} else {
  console.log('Usage:');
  console.log('  npx ts-node scripts/update-pricing.ts --validate  # Check and update prices');
  console.log('  npx ts-node scripts/update-pricing.ts --report    # Generate pricing report');
  
  // Default: show report
  generatePricingReport();
}
