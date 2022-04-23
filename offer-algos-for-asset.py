import sys
from pyteal import *

"""
Helps people offer Algos for assets.
"""
def approval_program(buyer_address, platform_address, asset_id, asset_price, platform_fee, init_fee, royalty_address, royalty_fee):
    # Template vars.
    buyer_address_tmpl = Tmpl.Addr(buyer_address)
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
    Seller accepts offer.
    """
    def seller_accepts_offer():
        ESCROW = Gtxn[0].sender()
        SELLER = Gtxn[2].sender()
        return And(
            *verify_group_of_txns(size = 3),

            # Escrow address is unique.
            ESCROW != buyer_address_tmpl,
            ESCROW != SELLER,

            # Escrow pays seller.
            Gtxn[0].type_enum() == TxnType.Payment,
            Gtxn[0].sender() == ESCROW,
            Gtxn[0].receiver() == SELLER,
            Gtxn[0].amount() == asset_price_tmpl,
            Gtxn[0].close_remainder_to() == Global.zero_address(),

            # Escrow pays creator and closes remainder to platform.
            Gtxn[1].type_enum() == TxnType.Payment,
            Gtxn[1].sender() == ESCROW,
            Gtxn[1].receiver() == royalty_address_tmpl,
            Gtxn[1].amount() == royalty_fee_tmpl,
            Gtxn[1].close_remainder_to() == platform_address_tmpl,

            # Seller sends asset.
            Gtxn[2].type_enum() == TxnType.AssetTransfer,
            Gtxn[2].sender() == SELLER,
            Gtxn[2].asset_receiver() == buyer_address_tmpl,
            Gtxn[2].asset_amount() == Int(1),
            Gtxn[2].xfer_asset() == asset_id_tmpl,
            Gtxn[2].asset_close_to() == Global.zero_address(),
        )

    """
    Buyer withdraws offer.
    """
    def buyer_withdraws_offer():
        ESCROW = Gtxn[1].sender()
        return And(
            *verify_group_of_txns(size = 2),

            # Escrow address is unique.
            ESCROW != buyer_address_tmpl,

            # Buyer approves txn group.
            Gtxn[0].type_enum() == TxnType.Payment,
            Gtxn[0].sender() == buyer_address_tmpl,
            Gtxn[0].receiver() == buyer_address_tmpl,
            Gtxn[0].amount() == Int(0),
            Gtxn[0].close_remainder_to() == Global.zero_address(),

            # Escrow refunds buyer.
            Gtxn[1].type_enum() == TxnType.Payment,
            Gtxn[1].sender() == ESCROW,
            Gtxn[1].receiver() == buyer_address_tmpl,
            Gtxn[1].amount() == asset_price_tmpl + royalty_fee_tmpl + platform_fee_tmpl,
            Gtxn[1].close_remainder_to() == platform_address_tmpl,
        )

    program = Cond(
        [buyer_withdraws_offer(), Approve()],
        [seller_accepts_offer(), Approve()],
    )

    return compileTeal(program, Mode.Signature, version=5)

if __name__ == '__main__':
    output = approval_program(
        buyer_address="TMPL_BUYER_ADDRESS",
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
