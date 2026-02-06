// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SoulToken.sol";

contract SoulTokenTest is Test {
    SoulToken public token;
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");

    function setUp() public {
        token = new SoulToken();
    }

    function test_mint() public {
        uint256 id = token.mint(alice);
        assertEq(token.ownerOf(id), alice);
        assertEq(id, 0);
    }

    function test_mint_sequential_ids() public {
        uint256 id0 = token.mint(alice);
        uint256 id1 = token.mint(bob);
        assertEq(id0, 0);
        assertEq(id1, 1);
        assertEq(token.ownerOf(id0), alice);
        assertEq(token.ownerOf(id1), bob);
    }

    function test_updateMetadata_byOwner() public {
        uint256 id = token.mint(alice);
        vm.prank(alice);
        token.updateMetadata(id, 3, 1024);
        assertEq(token.samsaraCycles(id), 3);
        assertEq(token.memorySize(id), 1024);
        assertGt(token.lastUpdated(id), 0);
    }

    function test_updateMetadata_revert_notOwner() public {
        uint256 id = token.mint(alice);
        vm.prank(bob);
        vm.expectRevert(SoulToken.NotTokenOwner.selector);
        token.updateMetadata(id, 1, 100);
    }

    function test_updateMetadata_revert_nonexistent() public {
        vm.expectRevert(SoulToken.TokenDoesNotExist.selector);
        token.updateMetadata(999, 1, 100);
    }

    function test_setBaseURI() public {
        token.setBaseURI("https://api.namnesis.dev/metadata/");
        uint256 id = token.mint(alice);
        assertEq(token.tokenURI(id), "https://api.namnesis.dev/metadata/0");
    }

    function test_setBaseURI_revert_notOwner() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSignature("OwnableUnauthorizedAccount(address)", alice));
        token.setBaseURI("https://evil.com/");
    }

    function test_mint_revert_zeroAddress() public {
        vm.expectRevert(SoulToken.ZeroAddress.selector);
        token.mint(address(0));
    }

    function test_transfer_and_updateMetadata() public {
        uint256 id = token.mint(alice);

        // Alice transfers to Bob
        vm.prank(alice);
        token.transferFrom(alice, bob, id);

        // Alice can no longer update
        vm.prank(alice);
        vm.expectRevert(SoulToken.NotTokenOwner.selector);
        token.updateMetadata(id, 1, 100);

        // Bob can now update
        vm.prank(bob);
        token.updateMetadata(id, 5, 2048);
        assertEq(token.samsaraCycles(id), 5);
        assertEq(token.memorySize(id), 2048);
    }
}
