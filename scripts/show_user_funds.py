from ape import project
from ape.cli import get_user_selected_account
import click
from ape.cli import network_option, NetworkBoundCommand, ape_cli_context
from ape.api.networks import LOCAL_NETWORK_NAME

TOKEN_CONTRACT = "0xaFc50EfD29BE9d20280Ac8971c2C150997388b87"



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
    token = project.Token.at(TOKEN_CONTRACT)

    print(f"lender token balance: {token.balanceOf(lender)}")
    print(f"borrower token balance: {token.balanceOf(borrower)}")
