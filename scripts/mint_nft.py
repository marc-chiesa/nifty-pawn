from ape import project
from ape.cli import get_user_selected_account
import click
from ape.cli import network_option, NetworkBoundCommand, ape_cli_context
from ape.api.networks import LOCAL_NETWORK_NAME

NFT_CONTRACT = "0xCf149676e251d37C1925c4993ac43F0E064AeBAB"



# default connect to a provider
def main():
    pass


#perk you can add args unlike main method
@click.command(cls=NetworkBoundCommand)
@ape_cli_context()
@network_option()
# cli_ctx must go first
def cli(cli_ctx, network):
    """
    Deploy all contracts
    """
    borrower = get_user_selected_account("Select borrower")
    broker = get_user_selected_account("Select broker")
    nft = project.NFT.at(NFT_CONTRACT)
    
    nft.mint(borrower, sender=broker, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    print(f"balance of borrower: {nft.balanceOf(borrower)}")
    assert(nft.ownerOf(0) == borrower.address)
