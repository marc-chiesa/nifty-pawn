from ape import project
from ape.cli import get_user_selected_account
import click
from ape.cli import network_option, NetworkBoundCommand, ape_cli_context
from ape.api.networks import LOCAL_NETWORK_NAME

TOKEN_CONTRACT = "0x3bBF90A454941368B9DCc06581dA11d806217540"



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
    lender = get_user_selected_account("Select lender")
    broker = get_user_selected_account("Select broker")
    token = project.Token.at(TOKEN_CONTRACT)
    
    token.transfer(borrower, 1000000, sender=broker, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    token.transfer(lender, 1000000, sender=broker, gas_limit=100000000, gas_price=0, max_fee="0 gwei", max_priority_fee="0 gwei")
    assert(token.balanceOf(borrower) == token.balanceOf(lender) == 1000000)
