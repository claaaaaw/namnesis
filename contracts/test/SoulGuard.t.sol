// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SoulToken.sol";
import "../src/SoulGuard.sol";
import "../src/interfaces/IOwnableExecutor.sol";
import "../src/interfaces/IECDSAValidator.sol";

/// @dev Mock OwnableExecutor that records calls for verification
contract MockOwnableExecutor is IOwnableExecutor {
    struct Call {
        address account;
        bytes data;
    }

    Call[] public calls;

    function executeOnOwnedAccount(
        address account,
        bytes calldata data
    ) external override {
        calls.push(Call(account, data));
    }

    function callCount() external view returns (uint256) {
        return calls.length;
    }

    function lastCall() external view returns (address account, bytes memory data) {
        require(calls.length > 0, "No calls recorded");
        Call storage c = calls[calls.length - 1];
        return (c.account, c.data);
    }
}

contract SoulGuardTest is Test {
    SoulToken public token;
    SoulGuard public guard;
    MockOwnableExecutor public executor;

    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    address public charlie = makeAddr("charlie");
    address public ecdsaValidator = makeAddr("ecdsaValidator");
    address public kernelAddress = makeAddr("kernel");

    function setUp() public {
        token = new SoulToken();
        executor = new MockOwnableExecutor();
        guard = new SoulGuard(
            address(token),
            address(executor),
            ecdsaValidator
        );
    }

    // ============ Constructor Zero-Address Tests ============

    function test_constructor_revert_zeroSoulContract() public {
        vm.expectRevert(SoulGuard.ZeroAddress.selector);
        new SoulGuard(address(0), address(executor), ecdsaValidator);
    }

    function test_constructor_revert_zeroExecutor() public {
        vm.expectRevert(SoulGuard.ZeroAddress.selector);
        new SoulGuard(address(token), address(0), ecdsaValidator);
    }

    function test_constructor_revert_zeroValidator() public {
        vm.expectRevert(SoulGuard.ZeroAddress.selector);
        new SoulGuard(address(token), address(executor), address(0));
    }

    // ============ Register Tests ============

    function test_register_revert_zeroKernel() public {
        uint256 soulId = token.mint(alice);

        vm.prank(alice);
        vm.expectRevert(SoulGuard.ZeroAddress.selector);
        guard.register(soulId, address(0));
    }

    function test_register_success() public {
        uint256 soulId = token.mint(alice);

        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        assertEq(guard.soulToKernel(soulId), kernelAddress);
        assertEq(guard.kernelToSoul(kernelAddress), soulId);
        assertEq(guard.confirmedOwner(soulId), alice);
        assertGt(guard.lastClaimTime(soulId), 0);
    }

    function test_register_revert_notOwner() public {
        uint256 soulId = token.mint(alice);

        vm.prank(bob);
        vm.expectRevert(SoulGuard.NotSoulOwner.selector);
        guard.register(soulId, kernelAddress);
    }

    function test_register_revert_duplicate() public {
        uint256 soulId = token.mint(alice);

        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        vm.prank(alice);
        vm.expectRevert(SoulGuard.KernelAlreadyRegistered.selector);
        guard.register(soulId, makeAddr("kernel2"));
    }

    function test_register_emits_event() public {
        uint256 soulId = token.mint(alice);

        vm.prank(alice);
        vm.expectEmit(true, true, false, true);
        emit SoulGuard.KernelRegistered(soulId, kernelAddress);
        guard.register(soulId, kernelAddress);
    }

    // ============ Claim Tests ============

    function test_claim_success() public {
        // Setup: Alice registers
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // Alice transfers NFT to Bob
        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);

        // Bob claims ownership
        vm.prank(bob);
        guard.claim(soulId);

        // Verify state
        assertEq(guard.confirmedOwner(soulId), bob);

        // Verify executor was called with correct data
        (address account, bytes memory data) = executor.lastCall();
        assertEq(account, kernelAddress);
        assertEq(
            data,
            abi.encodeCall(IECDSAValidator.changeOwner, (bob))
        );
    }

    function test_claim_revert_notOwner() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // Bob is not the NFT owner
        vm.prank(bob);
        vm.expectRevert(SoulGuard.NotSoulOwner.selector);
        guard.claim(soulId);
    }

    function test_claim_revert_notNeeded() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // Alice is already confirmed owner, no claim needed
        vm.prank(alice);
        vm.expectRevert(SoulGuard.ClaimNotNeeded.selector);
        guard.claim(soulId);
    }

    function test_claim_revert_noKernel() public {
        uint256 soulId = token.mint(alice);
        // Do NOT register kernel

        // Transfer to Bob
        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);

        // Bob tries to claim but no kernel registered
        vm.prank(bob);
        vm.expectRevert(SoulGuard.KernelNotRegistered.selector);
        guard.claim(soulId);
    }

    function test_claim_emits_event() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);

        vm.prank(bob);
        vm.expectEmit(true, true, true, true);
        emit SoulGuard.OwnershipClaimed(soulId, bob, kernelAddress);
        guard.claim(soulId);
    }

    // ============ isPendingClaim Tests ============

    function test_isPendingClaim_true() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // Transfer NFT but don't claim
        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);

        assertTrue(guard.isPendingClaim(soulId));
    }

    function test_isPendingClaim_false_afterClaim() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);

        // Claim
        vm.prank(bob);
        guard.claim(soulId);

        assertFalse(guard.isPendingClaim(soulId));
    }

    function test_isPendingClaim_false_noTransfer() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // No transfer happened
        assertFalse(guard.isPendingClaim(soulId));
    }

    // ============ isInClaimWindow Tests ============

    function test_isInClaimWindow_afterRegister() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        assertTrue(guard.isInClaimWindow(soulId));
    }

    function test_isInClaimWindow_expired() public {
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);

        // Warp past CLAIM_WINDOW (1 hour)
        vm.warp(block.timestamp + 2 hours);

        assertFalse(guard.isInClaimWindow(soulId));
    }

    // ============ Full Resurrection Flow ============

    function test_full_resurrection_flow() public {
        // 1. Alice mints and registers
        uint256 soulId = token.mint(alice);
        vm.prank(alice);
        guard.register(soulId, kernelAddress);
        assertFalse(guard.isPendingClaim(soulId));

        // 2. Alice transfers to Bob (simulating marketplace sale)
        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);
        assertTrue(guard.isPendingClaim(soulId));

        // 3. Bob claims
        vm.prank(bob);
        guard.claim(soulId);
        assertFalse(guard.isPendingClaim(soulId));
        assertEq(guard.confirmedOwner(soulId), bob);

        // 4. Bob transfers to Charlie
        vm.prank(bob);
        token.transferFrom(bob, charlie, soulId);
        assertTrue(guard.isPendingClaim(soulId));

        // 5. Charlie claims
        vm.prank(charlie);
        guard.claim(soulId);
        assertFalse(guard.isPendingClaim(soulId));
        assertEq(guard.confirmedOwner(soulId), charlie);

        // Executor was called twice (Bob claim + Charlie claim)
        assertEq(executor.callCount(), 2);
    }
}
