# @version 0.3.9

from vyper.interfaces import ERC165
from vyper.interfaces import ERC721
from vyper.interfaces import ERC20

############ ERC-721 #############

# Interface for the contract called by safeTransferFrom()
interface ERC721Receiver:
    def onERC721Received(
            operator: address,
            owner: address,
            tokenId: uint256,
            data: Bytes[1024]
        ) -> bytes4: nonpayable

# Interface for ERC721Permit()
interface ERC721Permit:
    def permit(
            spender: address,
            tokenId: uint256,
            deadline: uint256,
            sig: Bytes[65]
        ) -> bool: nonpayable

# Interface for ERC20Permit()
interface ERC20Permit:
    def permit(
            owner: address,
            spender: address,
            amount: uint256,
            expiry: uint256,
            signature: Bytes[65]
        ) -> bool: nonpayable

enum PawnState:
    CREATED
    ACTIVE
    DEFAULTED
    REPAID

struct PawnTerms:
    nftVault: address
    nftId: uint256
    currency: address
    principal: uint256
    interest: uint256
    durationInSeconds: uint256

struct PawnData:
    terms: PawnTerms
    state: PawnState
    startTimestamp: uint256
    borrower: address
    lender: address


# @dev This emits when an NFT is listed as collateral for a loan.
# @param pawnId ID of the pawn data.
event PawnCreated:
    pawnId: indexed(uint256)

# @dev This emits when a listing of a pawned NFT is canceled.
# @param pawnId ID of the pawn data.
event PawnCanceled:
    pawnId: indexed(uint256)

# @dev This emits when the terms of the loan have been accepted by a
# lender and the loan has been funded.
# @param pawnId ID of the pawn data.
event PawnStarted:
    pawnId: indexed(uint256)

# @dev This emits when a borrower has repaid the balance of the
# loan and received the collateral NFT back.
# @param pawnId ID of the pawn data.
event PawnRepaid:
    pawnId: indexed(uint256)

# @dev This emits when a lender claims the NFT on a defaulted loan.
# @param pawnId ID of the pawn data.
event PawnDefaultClaimed:
    pawnId: indexed(uint256)

owner: public(address)

# @dev pawnId => PawnData
idToData: public(HashMap[uint256, PawnData])

nextPawnId: uint256

ERC165_ID_OF_ERC721: constant(bytes4) = 0x80ac58cd
ERC165_ID_OF_ERC721Permit: constant(bytes4) = 0x5604e225

@external
def __init__():
    """
    @dev Contract constructor.
    """
    self.owner = msg.sender
    self.nextPawnId = 1

@view
@internal
def _isPawnInState(pawnId: uint256, state: PawnState) -> bool:
    return self.idToData[pawnId].state == state

@view
@internal
def _pawnInDefault(pawnId: uint256) -> bool:
    data: PawnData = self.idToData[pawnId]
    return self._isPawnInState(pawnId, PawnState.ACTIVE) and block.timestamp >= (data.startTimestamp + data.terms.durationInSeconds)

@view
@internal
def _pawnIsRepayable(pawnId: uint256) -> bool:
    data: PawnData = self.idToData[pawnId]
    return self._isPawnInState(pawnId, PawnState.ACTIVE) and block.timestamp < (data.startTimestamp + data.terms.durationInSeconds)

@view
@internal
def _amountDue(pawnId: uint256) -> uint256:
    assert self._pawnIsRepayable(pawnId)
    data: PawnData = self.idToData[pawnId]
    return data.terms.principal + data.terms.interest

@view
@external
def stateOf(pawnId: uint256) -> PawnState:
    data: PawnData = self.idToData[pawnId]
    assert data.state != empty(PawnState)
    return data.state

@view
@external
def amountDue(pawnId: uint256) -> uint256:
    return self._amountDue(pawnId)

@pure
@external
def onERC721Received(operator: address, owner: address, tokenId: uint256, data: Bytes[1024]) -> bytes4:
    return method_id("onERC721Received(address,address,uint256,bytes)", output_type=bytes4)

@internal
def _defaultPawn(pawnId: uint256, lender: address):
    assert self._pawnInDefault(pawnId)

    data: PawnData = self.idToData[pawnId]
    self.idToData[pawnId].state = PawnState.DEFAULTED
    ERC721(data.terms.nftVault).safeTransferFrom(
        self,
        lender,
        data.terms.nftId,
        b""
    )

    log PawnDefaultClaimed(pawnId)

@external
def claimDefaulted(pawnId: uint256) -> bool:
    assert msg.sender == self.idToData[pawnId].lender
    self._defaultPawn(pawnId, msg.sender)
    return True

@external
def repay(pawnId: uint256, permitDeadline: uint256, permitSignature: Bytes[65]) -> bool:
    assert self._pawnIsRepayable(pawnId)
    due: uint256 = self._amountDue(pawnId)

    data: PawnData = self.idToData[pawnId]

    assert ERC20(data.terms.currency).balanceOf(msg.sender) >= due

    self.idToData[pawnId].state = PawnState.REPAID

    assert ERC20Permit(data.terms.currency).permit(msg.sender, self, due, permitDeadline, permitSignature)
    assert ERC20(data.terms.currency).transferFrom(msg.sender, data.lender, due)
    ERC721(data.terms.nftVault).safeTransferFrom(self, data.borrower, data.terms.nftId, b"")

    log PawnRepaid(pawnId)

    return True

@external
def acceptTermsAndFund(pawnId: uint256, permitDeadline: uint256, permitSignature: Bytes[65]) -> bool:
    data: PawnData = self.idToData[pawnId]
    assert data.state == PawnState.CREATED
    assert ERC20(data.terms.currency).balanceOf(msg.sender) >=data.terms.principal

    self.idToData[pawnId] = PawnData({
        terms: data.terms,
        state: PawnState.ACTIVE,
        startTimestamp: block.timestamp,
        borrower: data.borrower,
        lender: msg.sender
    })

    assert ERC20Permit(data.terms.currency).permit(msg.sender, self, data.terms.principal, permitDeadline, permitSignature)
    assert ERC20(data.terms.currency).transferFrom(msg.sender, data.borrower, data.terms.principal)

    log PawnStarted(pawnId)
    return True

@external
def cancelTerms(pawnId: uint256) -> bool:
    data: PawnData = self.idToData[pawnId]
    assert msg.sender == data.borrower
    assert data.state == PawnState.CREATED
    assert self == ERC721(data.terms.nftVault).ownerOf(data.terms.nftId)
    self.idToData[pawnId] = empty(PawnData)
    ERC721(data.terms.nftVault).safeTransferFrom(self, msg.sender, data.terms.nftId, b"")
    assert msg.sender == ERC721(data.terms.nftVault).ownerOf(data.terms.nftId)
    log PawnCanceled(pawnId)

    return True

@external
def createTermsWithCollateral(terms: PawnTerms, permitDeadline: uint256, permitSignature: Bytes[65]) -> uint256:
    assert terms.durationInSeconds > 0, "must have pawn positive duration"
    assert block.timestamp < permitDeadline, "nft permit expired"
    assert self.idToData[self.nextPawnId].state == empty(PawnState), "invalid contract state"
    # verify that vault supports ERC721
    assert ERC165(terms.nftVault).supportsInterface(ERC165_ID_OF_ERC721), "vault must support ERC721"
    assert ERC165(terms.nftVault).supportsInterface(ERC165_ID_OF_ERC721Permit), "vault must support ERC721Permit"
    # sender only allowed to pawn an owned NFT 
    assert msg.sender == ERC721(terms.nftVault).ownerOf(terms.nftId), "sender must own nft"

    pawnId: uint256 = self.nextPawnId
    self.nextPawnId += 1

    pawnData: PawnData = PawnData({
        terms: terms,
        state: PawnState.CREATED,
        startTimestamp: empty(uint256),
        borrower: msg.sender,
        lender: empty(address)
    })
    self.idToData[pawnId] = pawnData

    assert ERC721Permit(terms.nftVault).permit(self, terms.nftId, permitDeadline, permitSignature), "permit failed"
    ERC721(terms.nftVault).safeTransferFrom(msg.sender, self, terms.nftId, b"")
    assert self == ERC721(terms.nftVault).ownerOf(terms.nftId), "contract does not own nft"

    log PawnCreated(pawnId)

    return pawnId