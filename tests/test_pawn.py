import ape
import pytest

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

def test_init(pawn, owner):
    assert pawn.owner() == owner
    with ape.reverts():
        print(pawn.stateOf(0))
    with ape.reverts():
        print(pawn.stateOf(1))

def mint_nft(nft, owner, receiver):
    tx = nft.mint(receiver, sender=owner)
    logs = list(tx.decode_logs(nft.Transfer))
    assert len(logs) == 1
    assert logs[0].receiver == receiver
    nft_id = logs[0].tokenId
    assert nft.ownerOf(nft_id) == receiver.address
    assert nft.idToApprovals(nft_id) == ZERO_ADDRESS
    return nft_id

def generateNftPermitSignature(nft, Permit, owner, approved, nft_id, deadline):
    nonce = nft.nonces(nft_id)
    permit = Permit(approved.address, nft_id, nonce, deadline)
    return owner.sign_message(permit.signable_message).encode_rsv()

def generateTokenPermitSignature(token, Permit, owner, approved, amount, deadline):
    nonce = token.nonces(owner)
    permit = Permit(owner.address, approved.address, amount, nonce, deadline)
    return owner.sign_message(permit.signable_message).encode_rsv()

def test_create_terms_with_collateral(chain, pawn, nft, token, owner, borrower, NFTPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)

    amount = 100
    interest = 1
    duration = 10

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    expectedPawnId = 1
    tx = pawn.createTermsWithCollateral(terms, deadline, permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert logs[0].pawnId == expectedPawnId
    assert pawn.idToData(expectedPawnId).state == 1
    assert pawn.idToData(expectedPawnId).startTimestamp == 0
    assert pawn.idToData(expectedPawnId).borrower == borrower.address
    assert pawn.idToData(expectedPawnId).lender == ZERO_ADDRESS
    assert nft.ownerOf(nft_id) == pawn.address

def test_create_terms_with_bad_nft(chain, pawn, nft, token, borrower, NFTPermit):
    nft_id = 100
    nonce = nft.nonces(borrower)
    deadline = chain.pending_timestamp + 60
    permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)

    amount = 100
    interest = 1
    duration = 10

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    with ape.reverts():
        pawn.createTermsWithCollateral(terms, deadline, permit, sender=borrower)

def test_create_terms_zero_duration(chain, pawn, nft, token, owner, borrower, NFTPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)

    amount = 100
    interest = 1
    duration = 0

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    with ape.reverts():
        pawn.createTermsWithCollateral(terms, deadline, permit, sender=borrower)

def test_create_terms_expired_permit(chain, pawn, nft, token, owner, borrower, NFTPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    chain.pending_timestamp += 100
    permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)

    amount = 100
    interest = 1
    duration = 0

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    with ape.reverts():
        pawn.createTermsWithCollateral(terms, deadline, permit, sender=borrower)

def test_cancel_terms(chain, pawn, nft, token, owner, borrower, NFTPermit, TokenPermit, lender):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)

    amount = 100
    interest = 1
    duration = 10

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId
    nft_id = pawn.idToData(pawn_id).terms.nftId
    assert nft.ownerOf(nft_id) == pawn.address
    assert pawn.stateOf(pawn_id) == 1
    tx = pawn.cancelTerms(pawn_id, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCanceled))
    assert len(logs) == 1
    assert logs[0].pawnId == pawn_id
    assert nft.ownerOf(nft_id) == borrower.address
    assert pawn.idToData(pawn_id).state == 0
    logs = list(tx.decode_logs(nft.Transfer))
    print(f"cancel transfer: {logs[0].sender}, {logs[0].receiver}, {logs[0].tokenId}")


def test_accept_terms(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)
    logs = list(tx.decode_logs(pawn.PawnStarted))
    assert pawn.stateOf(pawn_id) == 2
    assert len(logs) == 1
    assert token.balanceOf(lender) == 0
    assert token.balanceOf(borrower) == amount


def test_accept_terms_insufficient_funds(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId
    
    with ape.reverts():
        pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)
    
def test_accept_terms_bad_permit(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId
    
    with ape.reverts():
        pawn.acceptTermsAndFund(pawn_id, deadline + 1, token_permit, sender=lender)

def test_repay(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)

    token.transfer(borrower, interest, sender=owner)
    assert token.balanceOf(borrower) == amount + interest

    token_permit = generateTokenPermitSignature(token, TokenPermit, borrower, pawn, amount + interest, deadline)
    tx = pawn.repay(pawn_id, deadline, token_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnRepaid))
    assert len(logs) == 1
    assert logs[0].pawnId == pawn_id
    assert token.balanceOf(lender) == amount + interest
    assert token.balanceOf(borrower) == 0
    assert nft.ownerOf(nft_id) == borrower.address
    assert pawn.stateOf(pawn_id) == 8

def test_repay_insufficient_funds(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)

    token_permit = generateTokenPermitSignature(token, TokenPermit, borrower, pawn, amount + interest, deadline)
    with ape.reverts():
        pawn.repay(pawn_id, deadline, token_permit, sender=borrower)


def test_repay_late(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)

    chain.pending_timestamp += 10

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount

    token_permit = generateTokenPermitSignature(token, TokenPermit, borrower, pawn, amount + interest, deadline)
    with ape.reverts():
        pawn.repay(pawn_id, deadline, token_permit, sender=borrower)

def test_claim(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)

    chain.pending_timestamp += 10

    tx = pawn.claimDefaulted(pawn_id, sender=lender)
    logs = list(tx.decode_logs(pawn.PawnDefaultClaimed))
    assert len(logs) == 1
    assert logs[0].pawnId == pawn_id
    assert nft.ownerOf(nft_id) == lender.address
    assert token.balanceOf(borrower) == amount
    assert token.balanceOf(lender) == 0

def test_claim_too_early(chain, pawn, nft, token, owner, borrower, lender, NFTPermit, TokenPermit):
    nft_id = mint_nft(nft, owner, borrower)
    deadline = chain.pending_timestamp + 60
    amount = 100
    interest = 1
    duration = 10
    nft_permit = generateNftPermitSignature(nft, NFTPermit, borrower, pawn, nft_id, deadline)
    token_permit = generateTokenPermitSignature(token, TokenPermit, lender, pawn, amount, deadline)

    terms = (nft.address, nft_id, token.address, amount, interest, duration)

    tx = pawn.createTermsWithCollateral(terms, deadline, nft_permit, sender=borrower)
    logs = list(tx.decode_logs(pawn.PawnCreated))
    assert len(logs) == 1
    pawn_id = logs[0].pawnId

    token.transfer(lender, amount, sender=owner)
    assert token.balanceOf(lender) == amount
    
    tx = pawn.acceptTermsAndFund(pawn_id, deadline, token_permit, sender=lender)
    chain.pending_timestamp += 8

    with ape.reverts():
        pawn.claimDefaulted(pawn_id, sender=lender)