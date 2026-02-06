/**
 * ECDSA Verification + On-chain NFT Ownership Check
 *
 * Replaces the old Ed25519 signature verification with:
 * 1. ECDSA signature recovery (recover signer address from signature)
 * 2. On-chain read: ownerOf(soulId) == signer
 */

import {
  createPublicClient,
  http,
  recoverMessageAddress,
  type Address,
  type PublicClient,
  type Hex,
} from "viem";
import { baseSepolia } from "viem/chains";
import { soulTokenAbi } from "./abi";

export interface VerifyResult {
  valid: boolean;
  signer?: Address;
  owner?: Address;
  error?: string;
}

/**
 * Create a public client for on-chain reads (no private key needed).
 */
export function createChainClient(rpcUrl: string): PublicClient {
  return createPublicClient({
    chain: baseSepolia,
    transport: http(rpcUrl),
  });
}

/**
 * Recover the signer address from an ECDSA-signed message.
 *
 * The message format is: `${capsule_id}:${action}:${soul_id}:${timestamp}`
 */
export async function recoverSigner(
  message: string,
  signature: Hex,
): Promise<Address> {
  return recoverMessageAddress({
    message,
    signature,
  });
}

/**
 * Check if a given address is the owner of a Soul NFT.
 */
export async function checkSoulOwnership(
  client: PublicClient,
  soulTokenAddress: Address,
  soulId: bigint,
  expectedOwner: Address,
): Promise<VerifyResult> {
  try {
    const owner = await client.readContract({
      address: soulTokenAddress,
      abi: soulTokenAbi,
      functionName: "ownerOf",
      args: [soulId],
    });

    if ((owner as Address).toLowerCase() !== expectedOwner.toLowerCase()) {
      return {
        valid: false,
        signer: expectedOwner,
        owner: owner as Address,
        error: "Signer is not the Soul owner",
      };
    }

    return {
      valid: true,
      signer: expectedOwner,
      owner: owner as Address,
    };
  } catch (err) {
    return {
      valid: false,
      error: `Failed to check ownership: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * Full verification flow: recover signer from ECDSA signature,
 * then verify on-chain NFT ownership.
 */
export async function verifyEcdsaAndOwnership(
  client: PublicClient,
  soulTokenAddress: Address,
  message: string,
  signature: Hex,
  soulId: bigint,
): Promise<VerifyResult> {
  // 1. Recover signer from signature
  let signer: Address;
  try {
    signer = await recoverSigner(message, signature);
  } catch (err) {
    return {
      valid: false,
      error: `Invalid ECDSA signature: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  // 2. Check on-chain ownership
  return checkSoulOwnership(client, soulTokenAddress, soulId, signer);
}
