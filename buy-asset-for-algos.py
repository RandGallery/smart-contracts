import sys
from pyteal import *


def approval_program(asset_id, buyer_address, creator_address, creator_cut, platform_address, platform_cut, seller_address, seller_cut, deadline):
    # Template vars.
    asset_id_tmpl = Tmpl.Int(asset_id)
    buyer_address_tmpl = Tmpl.Addr(buyer_address)
    platform_address_tmpl = Tmpl.Addr(platform_address)
    platform_cut_tmpl = Tmpl.Int(platform_cut)
    creator_address_tmpl = Tmpl.Addr(creator_address)
    creator_cut_tmpl = Tmpl.Int(creator_cut)
    seller_address_tmpl = Tmpl.Addr(seller_address)
    seller_cut_tmpl = Tmpl.Int(seller_cut)
    deadline_tmpl = Tmpl.Int(deadline)

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

        # Prevent closing of accounts.
        for i in range(size):
            assertions.append(Gtxn[i].close_remainder_to()
                              == Global.zero_address())

        return assertions

    """
    Buys an asset with Algos.
    """
    def buy_asset():
        return And(
            # Verify basics.
            *verify_group_of_txns(size=5),

            # Check deadline.
            Gtxn[0].first_valid() < deadline_tmpl,

            # 1) Add asset.
            Gtxn[0].type_enum() == TxnType.AssetTransfer,
            Gtxn[0].sender() == buyer_address_tmpl,
            Gtxn[0].asset_receiver() == buyer_address_tmpl,
            Gtxn[0].asset_amount() == Int(0),
            Gtxn[0].xfer_asset() == asset_id_tmpl,
            Gtxn[0].asset_close_to() == Global.zero_address(),

            # 2) Send creator cut.
            Gtxn[1].type_enum() == TxnType.Payment,
            Gtxn[1].sender() == buyer_address_tmpl,
            Gtxn[1].receiver() == creator_address_tmpl,
            Gtxn[1].amount() == creator_cut_tmpl,

            # 3) Send seller cut.
            Gtxn[2].type_enum() == TxnType.Payment,
            Gtxn[2].sender() == buyer_address_tmpl,
            Gtxn[2].receiver() == seller_address_tmpl,
            Gtxn[2].amount() == seller_cut_tmpl,

            # 4) Send platform cut.
            Gtxn[3].type_enum() == TxnType.Payment,
            Gtxn[3].sender() == buyer_address_tmpl,
            Gtxn[3].receiver() == platform_address_tmpl,
            Gtxn[3].amount() == platform_cut_tmpl,

            # 5) Receive asset.
            Gtxn[4].type_enum() == TxnType.AssetTransfer,
            Gtxn[4].sender() != buyer_address_tmpl,
            Gtxn[4].asset_receiver() == buyer_address_tmpl,
            Gtxn[4].asset_amount() == Int(1),
            Gtxn[4].xfer_asset() == asset_id_tmpl,
        )

    program = Cond(
        [buy_asset(), Approve()],
    )

    return compileTeal(program, Mode.Signature, version=5)


if __name__ == '__main__':
    output = approval_program(
        asset_id="TMPL_ASSET_ID",
        buyer_address="TMPL_BUYER_ADDRESS",
        creator_address="TMPL_CREATOR_ADDRESS",
        creator_cut="TMPL_CREATOR_CUT",
        platform_address="TMPL_PLATFORM_ADDRESS",
        platform_cut="TMPL_PLATFORM_CUT",
        seller_address="TMPL_SELLER_ADDRESS",
        seller_cut="TMPL_SELLER_CUT",
        deadline="TMPL_DEADLINE",
    )
    sys.stdout.write(output)
    sys.stdout.flush()
    sys.exit(0)
