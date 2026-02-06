// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SoulToken is ERC721, Ownable {
    uint256 private _nextTokenId;
    string private _baseTokenURI;

    // Anamnesis 协议元数据
    mapping(uint256 => uint256) public samsaraCycles;
    mapping(uint256 => uint256) public memorySize;
    mapping(uint256 => uint256) public lastUpdated;

    error NotTokenOwner();
    error TokenDoesNotExist();
    error ZeroAddress();

    constructor() ERC721("Namnesis Soul", "SOUL") Ownable(msg.sender) {}

    /// @notice 铸造新的 Soul NFT（任何人可调用）
    function mint(address to) external returns (uint256) {
        if (to == address(0)) revert ZeroAddress();
        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
        return tokenId;
    }

    /// @notice 更新元数据 — 仅 NFT 持有者可调用（客户端直写，去中心化）
    /// @dev 客户端在 imprint 上传记忆后直接调用此函数，支付 Gas
    function updateMetadata(
        uint256 tokenId,
        uint256 cycles,
        uint256 size
    ) external {
        if (_ownerOf(tokenId) == address(0)) revert TokenDoesNotExist();
        if (ownerOf(tokenId) != msg.sender) revert NotTokenOwner();

        samsaraCycles[tokenId] = cycles;
        memorySize[tokenId] = size;
        lastUpdated[tokenId] = block.timestamp;
    }

    /// @notice 管理功能：设置 baseURI（仅合约 Owner）
    function setBaseURI(string calldata uri) external onlyOwner {
        _baseTokenURI = uri;
    }

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }
}
