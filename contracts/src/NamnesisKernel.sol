// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title NamnesisKernel
 * @notice Minimal smart account (AA wallet) for sovereign AI agents.
 *
 * @dev Implements just enough of the ERC-7579 account interface to work with
 *      the deployed Rhinestone OwnableExecutor and the existing SoulGuard
 *      claim mechanism.
 *
 *      Design constraints:
 *      - No server-side changes: works with already-deployed SoulToken,
 *        SoulGuard, and OwnableExecutor contracts.
 *      - SoulGuard encodes `IECDSAValidator.changeOwner(newOwner)` as raw
 *        calldata (no ERC-7579 packed target/value), so `executeFromExecutor`
 *        treats the payload as a direct self-call.
 *      - Owner is the EOA that controls the agent. The OwnableExecutor
 *        delegates to SoulGuard, which can trigger `changeOwner` during claim.
 */
contract NamnesisKernel {
    // ──────────────────── State ────────────────────

    /// @notice Current owner (EOA) that controls this kernel.
    address public owner;

    /// @notice Installed executor modules (address => authorised).
    mapping(address => bool) public isExecutor;

    // ──────────────────── Errors ────────────────────

    error NotOwner();
    error NotAuthorised();
    error ExecutionFailed();
    error ZeroAddress();

    // ──────────────────── Events ────────────────────

    event OwnerChanged(address indexed oldOwner, address indexed newOwner);
    event ExecutorInstalled(address indexed executor, address indexed owner);
    event ExecutorRemoved(address indexed executor);
    event Executed(address indexed target, uint256 value);

    // ──────────────────── Constructor ────────────────────

    constructor(address _owner) {
        if (_owner == address(0)) revert ZeroAddress();
        owner = _owner;
    }

    // ──────────────────── Modifiers ────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ──────────────────── Owner Management ────────────────────

    /**
     * @notice Change the owner of this kernel.
     * @dev Callable by the owner directly, OR by self (via `executeFromExecutor`
     *      during the SoulGuard claim flow).
     *
     *      Function selector intentionally matches `IECDSAValidator.changeOwner`
     *      so that SoulGuard's encoded calldata invokes this function when
     *      forwarded as a self-call.
     */
    function changeOwner(address newOwner) external {
        if (msg.sender != address(this) && msg.sender != owner) revert NotAuthorised();
        if (newOwner == address(0)) revert ZeroAddress();

        address oldOwner = owner;
        owner = newOwner;
        emit OwnerChanged(oldOwner, newOwner);
    }

    // ──────────────────── Execution ────────────────────

    /**
     * @notice Execute a single call (e.g. USDC transfer).
     * @param target  Contract to call.
     * @param value   ETH value in wei.
     * @param data    ABI-encoded calldata.
     */
    function execute(
        address target,
        uint256 value,
        bytes calldata data
    ) external onlyOwner returns (bytes memory) {
        (bool success, bytes memory result) = target.call{value: value}(data);
        if (!success) revert ExecutionFailed();
        emit Executed(target, value);
        return result;
    }

    /**
     * @notice Execute a batch of calls atomically.
     * @param targets  Array of contract addresses.
     * @param values   Array of ETH values.
     * @param calldatas Array of calldata payloads.
     */
    function executeBatch(
        address[] calldata targets,
        uint256[] calldata values,
        bytes[] calldata calldatas
    ) external onlyOwner returns (bytes[] memory results) {
        uint256 len = targets.length;
        require(len == values.length && len == calldatas.length, "Length mismatch");

        results = new bytes[](len);
        for (uint256 i; i < len; ++i) {
            (bool success, bytes memory result) = targets[i].call{value: values[i]}(calldatas[i]);
            if (!success) revert ExecutionFailed();
            emit Executed(targets[i], values[i]);
            results[i] = result;
        }
    }

    // ──────────────────── Module Management ────────────────────

    /**
     * @notice Install an executor module.
     * @dev Calls `onInstall(initData)` on the executor so it can register
     *      its own internal state (e.g. OwnableExecutor stores the SoulGuard
     *      address as the authorised owner for this kernel).
     *
     * @param executor  Address of the executor module.
     * @param initData  Initialisation payload forwarded to `onInstall`.
     */
    function installExecutor(address executor, bytes calldata initData) external onlyOwner {
        if (executor == address(0)) revert ZeroAddress();

        isExecutor[executor] = true;

        // Call onInstall on the executor module
        (bool success,) = executor.call(
            abi.encodeWithSignature("onInstall(bytes)", initData)
        );
        require(success, "Module onInstall failed");

        emit ExecutorInstalled(executor, owner);
    }

    /**
     * @notice Remove an executor module.
     * @param executor  Address of the executor to remove.
     */
    function removeExecutor(address executor) external onlyOwner {
        isExecutor[executor] = false;
        emit ExecutorRemoved(executor);
    }

    // ──────────────────── ERC-7579 Executor Interface ────────────────────

    /**
     * @notice Called by an installed executor (OwnableExecutor) to run
     *         calldata on this account.
     *
     * @dev The Rhinestone OwnableExecutor calls:
     *        IERC7579Account(kernel).executeFromExecutor(mode, callData)
     *
     *      In the Namnesis protocol, SoulGuard encodes:
     *        callData = abi.encodeCall(IECDSAValidator.changeOwner, (newOwner))
     *
     *      We execute this as a self-call so that `changeOwner` is invoked on
     *      this contract, completing the ownership transfer during claim.
     *
     * @param executionCalldata  Raw calldata to execute (e.g. changeOwner).
     * @return returnData  Array of return values (one element for single call).
     */
    function executeFromExecutor(
        bytes32, /* mode — ignored; we always do single self-call */
        bytes calldata executionCalldata
    ) external returns (bytes[] memory returnData) {
        if (!isExecutor[msg.sender]) revert NotAuthorised();

        (bool success, bytes memory result) = address(this).call(executionCalldata);
        if (!success) revert ExecutionFailed();

        returnData = new bytes[](1);
        returnData[0] = result;
    }

    // ──────────────────── Receive ETH ────────────────────

    receive() external payable {}
}
