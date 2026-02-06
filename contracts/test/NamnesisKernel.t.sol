// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/NamnesisKernel.sol";
import "../src/SoulToken.sol";
import "../src/SoulGuard.sol";
import "../src/interfaces/IOwnableExecutor.sol";
import "../src/interfaces/IECDSAValidator.sol";

/// @dev Minimal ERC-20 mock for USDC-like token testing
contract MockERC20 {
    string public name = "Mock USDC";
    string public symbol = "USDC";
    uint8 public decimals = 6;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        return true;
    }
}

/// @dev Mock executor that mimics OwnableExecutor's behaviour for testing.
///      Records onInstall calls and can forward executeFromExecutor.
contract MockExecutorForKernel {
    address public installedOwner;
    bool public installed;

    function onInstall(bytes calldata data) external {
        installed = true;
        installedOwner = address(bytes20(data[0:20]));
    }

    /// @dev Simulates OwnableExecutor: calls executeFromExecutor on the kernel
    function forwardExecute(address kernel, bytes calldata callData) external {
        NamnesisKernel(payable(kernel)).executeFromExecutor(
            bytes32(0), // mode (ignored by NamnesisKernel)
            callData
        );
    }
}

contract NamnesisKernelTest is Test {
    NamnesisKernel public kernel;
    MockERC20 public usdc;
    MockExecutorForKernel public mockExecutor;

    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    address public soulGuardAddr = makeAddr("soulGuard");

    function setUp() public {
        kernel = new NamnesisKernel(alice);
        usdc = new MockERC20();
        mockExecutor = new MockExecutorForKernel();
    }

    // ============ Constructor Tests ============

    function test_constructor_setsOwner() public view {
        assertEq(kernel.owner(), alice);
    }

    function test_constructor_revert_zeroAddress() public {
        vm.expectRevert(NamnesisKernel.ZeroAddress.selector);
        new NamnesisKernel(address(0));
    }

    // ============ changeOwner Tests ============

    function test_changeOwner_byOwner() public {
        vm.prank(alice);
        kernel.changeOwner(bob);
        assertEq(kernel.owner(), bob);
    }

    function test_changeOwner_revert_notOwner() public {
        vm.prank(bob);
        vm.expectRevert(NamnesisKernel.NotAuthorised.selector);
        kernel.changeOwner(bob);
    }

    function test_changeOwner_revert_zeroAddress() public {
        vm.prank(alice);
        vm.expectRevert(NamnesisKernel.ZeroAddress.selector);
        kernel.changeOwner(address(0));
    }

    function test_changeOwner_emitsEvent() public {
        vm.prank(alice);
        vm.expectEmit(true, true, false, true);
        emit NamnesisKernel.OwnerChanged(alice, bob);
        kernel.changeOwner(bob);
    }

    // ============ execute Tests ============

    function test_execute_transfer_usdc() public {
        // Fund kernel with mock USDC
        usdc.mint(address(kernel), 1000e6);
        assertEq(usdc.balanceOf(address(kernel)), 1000e6);

        // Owner executes USDC transfer from kernel
        bytes memory transferCall = abi.encodeCall(MockERC20.transfer, (bob, 100e6));
        vm.prank(alice);
        kernel.execute(address(usdc), 0, transferCall);

        assertEq(usdc.balanceOf(bob), 100e6);
        assertEq(usdc.balanceOf(address(kernel)), 900e6);
    }

    function test_execute_send_eth() public {
        // Fund kernel with ETH
        vm.deal(address(kernel), 1 ether);

        // Owner sends ETH from kernel
        vm.prank(alice);
        kernel.execute(bob, 0.5 ether, "");

        assertEq(bob.balance, 0.5 ether);
        assertEq(address(kernel).balance, 0.5 ether);
    }

    function test_execute_revert_notOwner() public {
        vm.prank(bob);
        vm.expectRevert(NamnesisKernel.NotOwner.selector);
        kernel.execute(address(usdc), 0, "");
    }

    // ============ executeBatch Tests ============

    function test_executeBatch_multiTransfer() public {
        usdc.mint(address(kernel), 1000e6);
        address charlie = makeAddr("charlie");

        address[] memory targets = new address[](2);
        targets[0] = address(usdc);
        targets[1] = address(usdc);

        uint256[] memory values = new uint256[](2);

        bytes[] memory calldatas = new bytes[](2);
        calldatas[0] = abi.encodeCall(MockERC20.transfer, (bob, 100e6));
        calldatas[1] = abi.encodeCall(MockERC20.transfer, (charlie, 200e6));

        vm.prank(alice);
        kernel.executeBatch(targets, values, calldatas);

        assertEq(usdc.balanceOf(bob), 100e6);
        assertEq(usdc.balanceOf(charlie), 200e6);
        assertEq(usdc.balanceOf(address(kernel)), 700e6);
    }

    function test_executeBatch_revert_notOwner() public {
        address[] memory targets = new address[](0);
        uint256[] memory values = new uint256[](0);
        bytes[] memory calldatas = new bytes[](0);

        vm.prank(bob);
        vm.expectRevert(NamnesisKernel.NotOwner.selector);
        kernel.executeBatch(targets, values, calldatas);
    }

    // ============ installExecutor Tests ============

    function test_installExecutor_success() public {
        bytes memory initData = abi.encodePacked(soulGuardAddr);

        vm.prank(alice);
        kernel.installExecutor(address(mockExecutor), initData);

        assertTrue(kernel.isExecutor(address(mockExecutor)));
        assertTrue(mockExecutor.installed());
        assertEq(mockExecutor.installedOwner(), soulGuardAddr);
    }

    function test_installExecutor_revert_notOwner() public {
        vm.prank(bob);
        vm.expectRevert(NamnesisKernel.NotOwner.selector);
        kernel.installExecutor(address(mockExecutor), "");
    }

    function test_installExecutor_revert_zeroAddress() public {
        vm.prank(alice);
        vm.expectRevert(NamnesisKernel.ZeroAddress.selector);
        kernel.installExecutor(address(0), "");
    }

    // ============ removeExecutor Tests ============

    function test_removeExecutor() public {
        vm.prank(alice);
        kernel.installExecutor(address(mockExecutor), abi.encodePacked(soulGuardAddr));
        assertTrue(kernel.isExecutor(address(mockExecutor)));

        vm.prank(alice);
        kernel.removeExecutor(address(mockExecutor));
        assertFalse(kernel.isExecutor(address(mockExecutor)));
    }

    // ============ executeFromExecutor Tests ============

    function test_executeFromExecutor_changeOwner() public {
        // Install mock executor
        vm.prank(alice);
        kernel.installExecutor(address(mockExecutor), abi.encodePacked(soulGuardAddr));

        // Executor forwards changeOwner call (simulates SoulGuard claim)
        bytes memory changeOwnerData = abi.encodeCall(
            IECDSAValidator.changeOwner,
            (bob)
        );
        mockExecutor.forwardExecute(address(kernel), changeOwnerData);

        assertEq(kernel.owner(), bob);
    }

    function test_executeFromExecutor_revert_notExecutor() public {
        bytes memory changeOwnerData = abi.encodeCall(
            IECDSAValidator.changeOwner,
            (bob)
        );

        // Direct call from non-executor should revert
        vm.prank(bob);
        vm.expectRevert(NamnesisKernel.NotAuthorised.selector);
        kernel.executeFromExecutor(bytes32(0), changeOwnerData);
    }

    // ============ Full Claim Flow with SoulGuard ============

    function test_full_claim_flow() public {
        // This test uses SoulToken + SoulGuard + MockOwnableExecutor
        // to simulate the real claim flow, but with our NamnesisKernel
        // instead of a placeholder kernel address.

        SoulToken token = new SoulToken();
        MockOwnableExecutorForClaim executor = new MockOwnableExecutorForClaim();
        SoulGuard guard = new SoulGuard(
            address(token),
            address(executor),
            makeAddr("ecdsaValidator")
        );

        // 1. Alice mints Soul NFT
        uint256 soulId = token.mint(alice);

        // 2. Alice deploys her kernel
        vm.prank(alice);
        NamnesisKernel aliceKernel = new NamnesisKernel(alice);

        // 3. Alice registers kernel with SoulGuard
        vm.prank(alice);
        guard.register(soulId, address(aliceKernel));
        assertEq(guard.soulToKernel(soulId), address(aliceKernel));

        // 4. Alice installs executor (so it can call executeFromExecutor)
        //    In production, this would be the real OwnableExecutor.
        //    Here we use a mock that forwards to executeFromExecutor.
        vm.prank(alice);
        aliceKernel.installExecutor(
            address(executor),
            abi.encodePacked(address(guard))
        );

        // 5. Alice transfers Soul NFT to Bob
        vm.prank(alice);
        token.transferFrom(alice, bob, soulId);
        assertTrue(guard.isPendingClaim(soulId));

        // 6. Bob claims - SoulGuard calls executor.executeOnOwnedAccount
        //    which calls kernel.executeFromExecutor with changeOwner(bob)
        vm.prank(bob);
        guard.claim(soulId);

        // 7. Verify ownership changed
        assertEq(aliceKernel.owner(), bob);
        assertFalse(guard.isPendingClaim(soulId));
        assertEq(guard.confirmedOwner(soulId), bob);
    }

    // ============ Receive ETH ============

    function test_receive_eth() public {
        vm.deal(alice, 1 ether);
        vm.prank(alice);
        (bool success,) = address(kernel).call{value: 1 ether}("");
        assertTrue(success);
        assertEq(address(kernel).balance, 1 ether);
    }
}

/// @dev Mock executor that actually calls executeFromExecutor on the kernel,
///      simulating the real OwnableExecutor behaviour during claim.
contract MockOwnableExecutorForClaim is IOwnableExecutor {
    // account => installed
    mapping(address => bool) public accountInstalled;

    function onInstall(bytes calldata) external {
        accountInstalled[msg.sender] = true;
    }

    function executeOnOwnedAccount(
        address account,
        bytes calldata data
    ) external override {
        // Simulate what OwnableExecutor does: call executeFromExecutor on the account
        NamnesisKernel(payable(account)).executeFromExecutor(bytes32(0), data);
    }
}
