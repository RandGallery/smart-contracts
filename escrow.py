import sys
from pyteal import *

"""
Helps people sell 1/1 indivisible NFTs.
"""
def approval_program(seller_address, platform_address, asset_id, asset_price, platform_fee, init_fee, royalty_address, royalty_fee):
    # Template vars.
    seller_address_tmpl = Tmpl.Addr(seller_address)
    platform_address_tmpl = Tmpl.Addr(platform_address)
    asset_id_tmpl = Tmpl.Int(asset_id)
    asset_price_tmpl = Tmpl.Int(asset_price)
    platform_fee_tmpl = Tmpl.Int(platform_fee)
    init_fee_tmpl = Tmpl.Int(init_fee)
    royalty_address_tmpl = Tmpl.Addr(royalty_address)
    royalty_fee_tmpl = Tmpl.Int(royalty_fee)

    """
    Verifies group size, fees, and rekeys.
    """
    def verify_group_of_txns(size):
        assertions = []

        # Verify group is correctly sized.
        assertions.append(Global.group_size() == Int(size))

        # Verify fees are reasonable.
        for i in range(size):
            assertions.append(Gtxn[i].fee() == Global.min_txn_fee())

        # Prevent clawbacks.
        for i in range(size):
            assertions.append(Gtxn[i].asset_sender() == Global.zero_address())

        # Prevent leases.
        for i in range(size):
            assertions.append(Gtxn[i].lease() == Global.zero_address())

        # Prevent rekeys.
        for i in range(size):
            assertions.append(Gtxn[i].rekey_to() == Global.zero_address())

        return assertions

    """
    Seller lists an NFT.
    """
    def seller_lists_nft_condition():
        ESCROW = Gtxn[0].receiver()
        return And(
            *verify_group_of_txns(size = 3),

            # 1) Seller funds escrow.
            Gtxn[0].type_enum() == TxnType.Payment,
            Gtxn[0].sender() == seller_address_tmpl,
            Gtxn[0].receiver() == ESCROW,
            Gtxn[0].amount() == init_fee_tmpl,
            Gtxn[0].close_remainder_to() == Global.zero_address(),

            # 2) Escrow accepts ASA.
            Gtxn[1].type_enum() == TxnType.AssetTransfer,
            Gtxn[1].sender() == ESCROW,
            Gtxn[1].asset_receiver() == ESCROW,
            Gtxn[1].asset_amount() == Int(0),
            Gtxn[1].xfer_asset() == asset_id_tmpl,
            Gtxn[1].asset_close_to() == Global.zero_address(),

            # 3) Seller sends ASA.
            Gtxn[2].type_enum() == TxnType.AssetTransfer,
            Gtxn[2].sender() == seller_address_tmpl,
            Gtxn[2].asset_receiver() == ESCROW,
            Gtxn[2].asset_amount() == Int(1),
            Gtxn[2].xfer_asset() == asset_id_tmpl,
            Gtxn[2].asset_close_to() == Global.zero_address(),
        )

    """
    Buyer purchases an NFT.
    """
    def buyer_purchases_nft_condition():
        BUYER = Gtxn[0].sender()
        ESCROW = Gtxn[4].sender()
        return And(
            *verify_group_of_txns(6),

            # The buyer and escrow accounts should be different.
            BUYER != ESCROW,

            # Buyer pays seller.
            Gtxn[0].type_enum() == TxnType.Payment,
            Gtxn[0].sender() == BUYER,
            Gtxn[0].receiver() == seller_address_tmpl,
            Gtxn[0].amount() == asset_price_tmpl,
            Gtxn[0].close_remainder_to() == Global.zero_address(),

            # Buyer pays platform.
            Gtxn[1].type_enum() == TxnType.Payment,
            Gtxn[1].sender() == BUYER,
            Gtxn[1].receiver() == platform_address_tmpl,
            Gtxn[1].amount() == platform_fee_tmpl,
            Gtxn[1].close_remainder_to() == Global.zero_address(),

            # Buyer pays creator.
            Gtxn[2].type_enum() == TxnType.Payment,
            Gtxn[2].sender() == BUYER,
            Gtxn[2].receiver() == royalty_address_tmpl,
            Gtxn[2].amount() == royalty_fee_tmpl,
            Gtxn[2].close_remainder_to() == Global.zero_address(),

            # Buyer accepts ASA.
            Gtxn[3].type_enum() == TxnType.AssetTransfer,
            Gtxn[3].sender() == BUYER,
            Gtxn[3].asset_receiver() == BUYER,
            Gtxn[3].asset_amount() == Int(0),
            Gtxn[3].xfer_asset() == asset_id_tmpl,
            Gtxn[3].asset_close_to() == Global.zero_address(),

            # Escrow sends ASA.
            Gtxn[4].type_enum() == TxnType.AssetTransfer,
            Gtxn[4].sender() == ESCROW,
            Gtxn[4].asset_receiver() == BUYER,
            Gtxn[4].asset_amount() == Int(1),
            Gtxn[4].xfer_asset() == asset_id_tmpl,
            Gtxn[4].asset_close_to() == BUYER,

            # Escrows refunds seller.
            Gtxn[5].type_enum() == TxnType.Payment,
            Gtxn[5].sender() == ESCROW,
            Gtxn[5].receiver() == seller_address_tmpl,
            Gtxn[5].amount() == Int(0),
            Gtxn[5].close_remainder_to() == seller_address_tmpl,
        )

    """
    Seller unlists an NFT.
    """
    def seller_unlists_nft():
        ESCROW = Gtxn[1].sender()
        return And(
            *verify_group_of_txns(3),

            # Seller accepts ASA.
            Gtxn[0].type_enum() == TxnType.AssetTransfer,
            Gtxn[0].sender() == seller_address_tmpl,
            Gtxn[0].asset_receiver() == seller_address_tmpl,
            Gtxn[0].asset_amount() == Int(0),
            Gtxn[0].xfer_asset() == asset_id_tmpl,
            Gtxn[0].asset_close_to() == Global.zero_address(),

            # Escrow sends ASA.
            Gtxn[1].type_enum() == TxnType.AssetTransfer,
            Gtxn[1].sender() == ESCROW,
            Gtxn[1].asset_receiver() == seller_address_tmpl,
            Gtxn[1].asset_amount() == Int(1),
            Gtxn[1].xfer_asset() == asset_id_tmpl,
            Gtxn[1].asset_close_to() == seller_address_tmpl,
            
            # Escrow refunds seller.
            Gtxn[2].type_enum() == TxnType.Payment,
            Gtxn[2].sender() == ESCROW,
            Gtxn[2].receiver() == seller_address_tmpl,
            Gtxn[2].amount() == Int(0),
            Gtxn[2].close_remainder_to() == seller_address_tmpl,
        )

    program = Cond(
        [seller_lists_nft_condition(), Approve()],
        [seller_unlists_nft(), Approve()],
        [buyer_purchases_nft_condition(), Approve()],
    )

    return compileTeal(program, Mode.Signature, version=5)

if __name__ == '__main__':
    output = approval_program(
        seller_address="TMPL_SELLER_ADDRESS",
        platform_address="TMPL_PLATFORM_ADDRESS",
        asset_id="TMPL_ASSET_ID",
        asset_price="TMPL_ASSET_PRICE",
        platform_fee="TMPL_PLATFORM_FEE",
        init_fee="TMPL_INIT_FEE",
        royalty_address="TMPL_ROYALTY_ADDRESS",
        royalty_fee="TMPL_ROYALTY_FEE"
    )
    sys.stdout.write(output)
    sys.stdout.flush()
    sys.exit(0)
