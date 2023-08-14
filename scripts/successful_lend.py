from ape import project
from ape import chain
from ape.cli import get_user_selected_account
import click
from ape.cli import network_option, NetworkBoundCommand, ape_cli_context
from ape.api.networks import LOCAL_NETWORK_NAME
from eip712.messages import EIP712Message

NFT_CONTRACT = "0xCf149676e251d37C1925c4993ac43F0E064AeBAB"
TOKEN_CONTRACT = "0x3bBF90A454941368B9DCc06581dA11d806217540"
PAWN_CONTRACT = "0x2F030c52eb0Fb9d60a57533347547707609dD73c"

PAWN_CREATED = 1 << 0
PAWN_STARTED = 1 << 1
PAWN_DEFAULTED = 1 << 2
PAWN_REPAID = 1 << 3

PERMIT_TIMEOUT = 120 # seconds

def getTokenPermit(chain, token, owner, spender, amount, deadline):
    class Permit(EIP712Message):
        _name_: "string" = "TokenTest"
        _version_: "string" = "1.0"
        _chainId_: "uint256" = chain.chain_id
        _verifyingContract_: "address" = token.address

        owner: "address"
        spender: "address"
        value: "uint256"
        nonce: "uint256"
        deadline: "uint256"
    
    nonce = token.nonces(owner)
    permit = Permit(owner.address, spender.address, amount, nonce, deadline)
    return owner.sign_message(permit.signable_message).encode_rsv()

def getNFTPermit(chain, nft, owner, spender, nft_id, deadline):
    class Permit(EIP712Message):
        _name_: "string" = "Owner NFT"
        _version_: "string" = "1.0"
        _chainId_: "uint256" = chain.chain_id
        _verifyingContract_: "address" = nft.address

        spender: "address"
        tokenId: "uint256"
        nonce: "uint256"
        deadline: "uint256"
    
    nonce = nft.nonces(nft_id)
    permit = Permit(spender.address, nft_id, nonce, deadline)
    return owner.sign_message(permit.signable_message).encode_rsv()

# default connect to a provider
def main():
    pass


#perk you can add args unlike main method
@click.command(cls=NetworkBoundCommand)
@ape_cli_context()
@network_option()
# cli_ctx must go first
def cli(cli_ctx, network):
    borrower = get_user_selected_account('Select borrower')
    lender = get_user_selected_account('Select lender')
    nft = project.NFT.at(NFT_CONTRACT)
    token = project.Token.at(TOKEN_CONTRACT)
    pawn = project.NiftyPawn.at(PAWN_CONTRACT)
    nft_id = 0
    loan_amount = 1000
    interest = 100
    time_to_repay = 120 # seconds

    print(f"borrower address: {borrower.address}")
    print(f"lender address: {lender.address}")
    print(f"borrower starting funds: {token.balanceOf(borrower)}")
    print(f"lender starting funds: {token.balanceOf(lender)}")

    terms = (nft.address, nft_id, token.address, loan_amount, interest, time_to_repay)
    deadline = PERMIT_TIMEOUT + chain.pending_timestamp
    borrower_nft_signature = getNFTPermit(chain, nft, borrower, pawn, nft_id, deadline)
    print(f"Owner of nft with id {nft_id} before creation is {nft.ownerOf(nft_id)}")
    tx = pawn.createTermsWithCollateral(terms, deadline, borrower_nft_signature, sender=borrower, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    print(f"Owner of nft with id {nft_id} after creation is {nft.ownerOf(nft_id)}")
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId
    print(f"Created pawn with id {pawn_id}")
    pawn_data = pawn.idToData(pawn_id)
    print(f"Terms: {pawn_data.terms}")

    deadline = PERMIT_TIMEOUT + chain.pending_timestamp
    lender_token_signature = getTokenPermit(chain, token, lender, pawn, loan_amount, deadline)
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, lender_token_signature, sender=lender, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    logs = list(tx.decode_logs(pawn.PawnStarted))
    assert len(logs) == 1
    print(f"Started pawn with id {pawn_id}")
    pawn_data = pawn.idToData(pawn_id)
    print(f"Pawn data: {pawn_data}")

    print(f"borrower funds: {token.balanceOf(borrower)}")
    print(f"lender funds: {token.balanceOf(lender)}")

    deadline = PERMIT_TIMEOUT + chain.pending_timestamp
    borrower_token_signature = getTokenPermit(chain, token, borrower, pawn, loan_amount + interest, deadline)
    tx = pawn.repay(pawn_id, deadline, borrower_token_signature, sender=borrower, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    logs = list(tx.decode_logs(pawn.PawnRepaid))
    assert len(logs) == 1
    print(f"Repaid pawn with id {pawn_id}")
    pawn_data = pawn.idToData(pawn_id)
    print(f"Pawn data: {pawn_data}")
    print(f"Owner of nft with id {pawn_data.terms.nftId} is {nft.ownerOf(pawn_data.terms.nftId)}")
    print(f"borrower funds: {token.balanceOf(borrower)}")
    print(f"lender funds: {token.balanceOf(lender)}")

    
    
