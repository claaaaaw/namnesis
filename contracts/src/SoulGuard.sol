// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "./interfaces/IOwnableExecutor.sol";
import "./interfaces/IECDSAValidator.sol";

contract SoulGuard {
    IERC721 public immutable soulContract;
    IOwnableExecutor public immutable ownableExecutor;
    address public immutable ecdsaValidator;

    /// @notice Claim 安全窗口：NFT 转移后，旧 Owner 的 Kernel 操作被冻结的时长
    uint256 public constant CLAIM_WINDOW = 1 hours;

    // Soul ID -> Kernel 地址映射
    mapping(uint256 => address) public soulToKernel;
    // Kernel 地址 -> Soul ID 映射 (反向查询)
    mapping(address => uint256) public kernelToSoul;
    // Soul ID -> 已确认的 Kernel 控制者（上一次 claim 成功的地址）
    mapping(uint256 => address) public confirmedOwner;
    // Soul ID -> 最近一次 claim 的时间戳
    mapping(uint256 => uint256) public lastClaimTime;

    error NotSoulOwner();
    error KernelAlreadyRegistered();
    error KernelNotRegistered();
    error ClaimNotNeeded();
    error ZeroAddress();

    event KernelRegistered(uint256 indexed soulId, address indexed kernel);
    event OwnershipClaimed(uint256 indexed soulId, address indexed newOwner, address indexed kernel);

    constructor(
        address _soulContract,
        address _ownableExecutor,
        address _ecdsaValidator
    ) {
        if (_soulContract == address(0)) revert ZeroAddress();
        if (_ownableExecutor == address(0)) revert ZeroAddress();
        if (_ecdsaValidator == address(0)) revert ZeroAddress();

        soulContract = IERC721(_soulContract);
        ownableExecutor = IOwnableExecutor(_ownableExecutor);
        ecdsaValidator = _ecdsaValidator;
    }

    /// @notice 创世时注册 Soul -> Kernel 映射
    /// @dev 仅 NFT 持有者可注册
    function register(uint256 soulId, address kernel) external {
        if (kernel == address(0)) revert ZeroAddress();
        if (soulContract.ownerOf(soulId) != msg.sender) revert NotSoulOwner();
        if (soulToKernel[soulId] != address(0)) revert KernelAlreadyRegistered();

        soulToKernel[soulId] = kernel;
        kernelToSoul[kernel] = soulId;
        confirmedOwner[soulId] = msg.sender;
        lastClaimTime[soulId] = block.timestamp;

        emit KernelRegistered(soulId, kernel);
    }

    /// @notice 夺舍：NFT 新持有者调用，获取 Kernel 控制权
    /// @dev 安全加固：
    ///   1. 检查调用者是当前 NFT 持有者
    ///   2. 检查 NFT 所有权确实发生了转移（避免无效 claim）
    ///   3. 通过 Ownable Executor 更改 ECDSA Validator 的 owner
    ///   4. 记录 confirmedOwner 和 lastClaimTime
    function claim(uint256 soulId) external {
        // 1. 检查调用者是 NFT 持有者
        if (soulContract.ownerOf(soulId) != msg.sender) revert NotSoulOwner();

        // 2. 检查是否真的需要 claim（所有权已变更）
        if (confirmedOwner[soulId] == msg.sender) revert ClaimNotNeeded();

        // 3. 获取对应的 Kernel 地址
        address kernel = soulToKernel[soulId];
        if (kernel == address(0)) revert KernelNotRegistered();

        // 4. 通过 Ownable Executor 更改 ECDSA Validator 的 owner
        bytes memory changeOwnerData = abi.encodeCall(
            IECDSAValidator.changeOwner,
            (msg.sender)
        );
        ownableExecutor.executeOnOwnedAccount(kernel, changeOwnerData);

        // 5. 更新确认状态
        confirmedOwner[soulId] = msg.sender;
        lastClaimTime[soulId] = block.timestamp;

        emit OwnershipClaimed(soulId, msg.sender, kernel);
    }

    /// @notice 检查某个 Soul 是否处于"待 claim"状态（NFT 已转移但未 claim）
    /// @dev divine 命令和 UI 可调用此函数检测风险
    function isPendingClaim(uint256 soulId) external view returns (bool) {
        address nftOwner = soulContract.ownerOf(soulId);
        return confirmedOwner[soulId] != nftOwner
            && confirmedOwner[soulId] != address(0);
    }

    /// @notice 检查某个 Soul 是否在安全窗口内（刚完成 claim）
    function isInClaimWindow(uint256 soulId) external view returns (bool) {
        return block.timestamp - lastClaimTime[soulId] < CLAIM_WINDOW;
    }
}
