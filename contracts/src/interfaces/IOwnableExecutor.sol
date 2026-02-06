// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IOwnableExecutor {
    function executeOnOwnedAccount(
        address account,
        bytes calldata data
    ) external;
}
