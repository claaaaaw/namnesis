/**
 * Namnesis Credential Service
 *
 * Cloudflare Worker that provides presigned URLs for R2 storage access.
 * Uses ECDSA signature verification + on-chain NFT ownership checks.
 *
 * Endpoints:
 * - POST /presign          - ECDSA verify + generate presigned URLs
 * - GET  /api/metadata/:id - Read on-chain SoulToken metadata (NFT JSON)
 * - GET  /health           - Health check
 */

import { AwsClient } from "aws4fetch";
import {
  createPublicClient,
  http,
  type Address,
  type PublicClient,
} from "viem";
import { baseSepolia } from "viem/chains";
import { soulTokenAbi, soulGuardAbi } from "./abi";
import { verifyEcdsaAndOwnership, createChainClient } from "./verify";
import type { Hex } from "viem";

// ============ Types ============

interface Env {
  R2: R2Bucket;
  R2_ACCESS_KEY_ID: string;
  R2_SECRET_ACCESS_KEY: string;
  R2_ACCOUNT_ID: string;
  R2_BUCKET_NAME: string;
  SOUL_TOKEN_ADDRESS: string;
  SOUL_GUARD_ADDRESS: string;
  BASE_SEPOLIA_RPC: string;
}

interface PresignRequest {
  capsule_id: string; // Format: owner_fp/uuid (kept for R2 path compat)
  soul_id: number; // On-chain Soul NFT token ID
  action: "read" | "write";
  blobs?: string[]; // For write: list of blob_ids to upload
  timestamp: number;
  signature: string; // hex-encoded ECDSA signature
}

// ============ CORS Configuration ============

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// ============ Environment Validation ============

const REQUIRED_ENV_VARS = [
  "R2_ACCESS_KEY_ID",
  "R2_SECRET_ACCESS_KEY",
  "R2_ACCOUNT_ID",
  "R2_BUCKET_NAME",
  "SOUL_TOKEN_ADDRESS",
  "SOUL_GUARD_ADDRESS",
  "BASE_SEPOLIA_RPC",
] as const;

function validateEnv(env: Env): string | null {
  for (const key of REQUIRED_ENV_VARS) {
    if (!env[key]) {
      return `Missing required environment variable: ${key}`;
    }
  }
  return null;
}

// ============ Main Handler ============

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext,
  ): Promise<Response> {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // Validate environment (skip for health check so we can diagnose)
    const url = new URL(request.url);
    if (url.pathname !== "/health") {
      const envError = validateEnv(env);
      if (envError) {
        return Response.json(
          { error: `Configuration error: ${envError}` },
          { status: 500, headers: corsHeaders },
        );
      }
    }

    // Health check
    if (url.pathname === "/health") {
      return Response.json(
        {
          status: "ok",
          version: "2.0.0",
          protocol: "namnesis",
          auth: "ecdsa+nft",
          timestamp: Math.floor(Date.now() / 1000),
        },
        { headers: corsHeaders },
      );
    }

    // Metadata endpoint: GET /api/metadata/:soulId
    const metadataMatch = url.pathname.match(/^\/api\/metadata\/(\d+)$/);
    if (metadataMatch && request.method === "GET") {
      return handleMetadata(parseInt(metadataMatch[1], 10), env);
    }

    // Presign endpoint
    if (url.pathname === "/presign" && request.method === "POST") {
      return handlePresign(request, env, ctx);
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  },
};

// ============ Metadata Handler ============

async function handleMetadata(
  soulId: number,
  env: Env,
): Promise<Response> {
  try {
    const client = createChainClient(env.BASE_SEPOLIA_RPC);
    const tokenAddress = env.SOUL_TOKEN_ADDRESS as Address;

    // Read on-chain metadata
    const [cycles, size, lastUpd, owner] = await Promise.all([
      client.readContract({
        address: tokenAddress,
        abi: soulTokenAbi,
        functionName: "samsaraCycles",
        args: [BigInt(soulId)],
      }),
      client.readContract({
        address: tokenAddress,
        abi: soulTokenAbi,
        functionName: "memorySize",
        args: [BigInt(soulId)],
      }),
      client.readContract({
        address: tokenAddress,
        abi: soulTokenAbi,
        functionName: "lastUpdated",
        args: [BigInt(soulId)],
      }),
      client.readContract({
        address: tokenAddress,
        abi: soulTokenAbi,
        functionName: "ownerOf",
        args: [BigInt(soulId)],
      }),
    ]);

    // Read SoulGuard data
    const guardAddress = env.SOUL_GUARD_ADDRESS as Address;
    const [kernel, pendingClaim] = await Promise.all([
      client.readContract({
        address: guardAddress,
        abi: soulGuardAbi,
        functionName: "soulToKernel",
        args: [BigInt(soulId)],
      }),
      client.readContract({
        address: guardAddress,
        abi: soulGuardAbi,
        functionName: "isPendingClaim",
        args: [BigInt(soulId)],
      }),
    ]);

    // Return NFT-compatible JSON metadata
    const metadata = {
      name: `Namnesis Soul #${soulId}`,
      description: "A sovereign AI agent soul on the Namnesis protocol.",
      image: `https://api.namnesis.dev/images/${soulId}`,
      attributes: [
        { trait_type: "Samsara Cycles", value: Number(cycles) },
        { trait_type: "Memory Size", value: Number(size) },
        { trait_type: "Last Updated", value: Number(lastUpd) },
        { trait_type: "Owner", value: owner },
        { trait_type: "Kernel", value: kernel },
        { trait_type: "Pending Claim", value: pendingClaim },
      ],
    };

    return Response.json(metadata, {
      headers: {
        ...corsHeaders,
        "Cache-Control": "public, max-age=60",
      },
    });
  } catch (err) {
    return Response.json(
      {
        error: `Failed to read metadata: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 500, headers: corsHeaders },
    );
  }
}

// ============ Presign Handler ============

async function handlePresign(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
): Promise<Response> {
  // Parse request body
  let body: PresignRequest;
  try {
    body = (await request.json()) as PresignRequest;
  } catch {
    return Response.json(
      { error: "Invalid JSON" },
      { status: 400, headers: corsHeaders },
    );
  }

  const { capsule_id, soul_id, action, blobs, timestamp, signature } = body;

  // 1. Validate capsule_id format
  const idParts = capsule_id.split("/");
  if (idParts.length !== 2) {
    return Response.json(
      { error: "Invalid capsule_id format, expected: owner_fp/uuid" },
      { status: 400, headers: corsHeaders },
    );
  }

  // 2. Validate soul_id
  if (typeof soul_id !== "number" || soul_id < 0) {
    return Response.json(
      { error: "Invalid soul_id" },
      { status: 400, headers: corsHeaders },
    );
  }

  // 3. Validate timestamp (5-minute window for replay protection)
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - timestamp) > 300) {
    return Response.json(
      { error: "Request expired" },
      { status: 401, headers: corsHeaders },
    );
  }

  // 4. Verify ECDSA signature + on-chain NFT ownership
  const message = `${capsule_id}:${action}:${soul_id}:${timestamp}`;
  const client = createChainClient(env.BASE_SEPOLIA_RPC);
  const tokenAddress = env.SOUL_TOKEN_ADDRESS as Address;

  const result = await verifyEcdsaAndOwnership(
    client,
    tokenAddress,
    message,
    signature as Hex,
    BigInt(soul_id),
  );

  if (!result.valid) {
    return Response.json(
      { error: result.error || "Verification failed" },
      { status: 403, headers: corsHeaders },
    );
  }

  // 5. Generate presigned URLs
  const expiresIn = 3600; // 1 hour
  const presigner = new R2Presigner(env);

  const urls: Record<string, unknown> = {};
  const prefix = `capsules/${capsule_id}`;

  try {
    if (action === "read") {
      // Read: generate GET URLs for manifest and all blobs
      urls.manifest = await presigner.presignGet(
        `${prefix}/capsule.manifest.json`,
        expiresIn,
      );
      urls.redaction_report = await presigner.presignGet(
        `${prefix}/redaction.report.json`,
        expiresIn,
      );

      // List all blobs and generate URLs
      const blobList = await env.R2.list({ prefix: `${prefix}/blobs/` });
      const blobUrls: Record<string, string> = {};
      for (const obj of blobList.objects) {
        const blobId = obj.key.split("/").pop()!;
        blobUrls[blobId] = await presigner.presignGet(obj.key, expiresIn);
      }
      urls.blobs = blobUrls;
    } else {
      // Write: generate PUT URLs for specified blobs
      urls.manifest = await presigner.presignPut(
        `${prefix}/capsule.manifest.json`,
        expiresIn,
      );
      urls.redaction_report = await presigner.presignPut(
        `${prefix}/redaction.report.json`,
        expiresIn,
      );

      const blobUrls: Record<string, string> = {};
      for (const blobId of blobs || []) {
        blobUrls[blobId] = await presigner.presignPut(
          `${prefix}/blobs/${blobId}`,
          expiresIn,
        );
      }
      urls.blobs = blobUrls;
    }
  } catch (err) {
    return Response.json(
      {
        error: `Storage operation failed: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 502, headers: corsHeaders },
    );
  }

  return Response.json(
    {
      expires_at: now + expiresIn,
      urls,
    },
    { headers: corsHeaders },
  );
}

// ============ R2 Presigner ============

class R2Presigner {
  private client: AwsClient;
  private endpoint: string;
  private bucket: string;

  constructor(env: Env) {
    this.client = new AwsClient({
      accessKeyId: env.R2_ACCESS_KEY_ID,
      secretAccessKey: env.R2_SECRET_ACCESS_KEY,
      service: "s3",
      region: "auto",
    });
    this.endpoint = `https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`;
    this.bucket = env.R2_BUCKET_NAME;
  }

  async presignGet(key: string, expiresIn: number): Promise<string> {
    const url = new URL(`${this.endpoint}/${this.bucket}/${key}`);
    const signed = await this.client.sign(url.toString(), {
      method: "GET",
      aws: { signQuery: true, expiresIn },
    });
    return signed.url;
  }

  async presignPut(key: string, expiresIn: number): Promise<string> {
    const url = new URL(`${this.endpoint}/${this.bucket}/${key}`);
    const signed = await this.client.sign(url.toString(), {
      method: "PUT",
      aws: { signQuery: true, expiresIn },
    });
    return signed.url;
  }
}
