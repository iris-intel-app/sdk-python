"""Response types of the Iris API (https://iriscan.app/developers), as TypedDicts.

Responses are plain ``dict``s; these types describe them for editors and type checkers. Field
names are the API's own. Times that are ``str`` are ISO 8601 in UTC; ``int`` times are Unix
seconds. Shares are 0 to 1. Keys the API leaves out when empty are in ``total=False`` bases.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict, Union

Chain = Literal["solana", "ethereum", "base", "arbitrum", "robinhood", "bsc", "dydx", "noble", "bitcoin", "tron"]
"""Every chain the API reads. Each route accepts the subset its docs list."""

EvmChain = Literal["ethereum", "base", "arbitrum", "robinhood", "bsc"]
InsidersChain = Literal["solana", "robinhood", "bsc"]
FollowChain = Literal["solana", "ethereum", "base", "arbitrum", "robinhood", "bsc", "bitcoin", "tron"]
TraceChain = FollowChain
KindChain = Literal["solana", "robinhood", "bsc"]
XchainWalletChain = Literal["solana", "ethereum", "base", "arbitrum", "robinhood", "bsc"]


class Credits(TypedDict, total=False):
    """What the account has left (the ``x-iris-credits`` header, and ``credits`` in /follow)."""

    plan: str
    plan_name: str
    cycle: str
    analyses_left: int
    traces_left: int
    pack_credits: int
    period_end: Optional[str]
    paid_until: Optional[str]


class RateLimit(TypedDict):
    limit: int
    remaining: int
    reset: int


# ------------------------------------------------------------------------------------------------
# POST /analyze
# ------------------------------------------------------------------------------------------------

Identity = TypedDict("Identity", {"type": str, "confidence": float})


class Risk(TypedDict):
    level: Literal["LOW", "MEDIUM", "HIGH"]
    score: int
    confidence: float


class Label(TypedDict):
    name: str
    category: str
    confidence: float
    source: str
    entity: Optional[str]
    source_url: Optional[str]
    role: Optional[str]


class LookalikePair(TypedDict):
    fake: str
    real: str
    real_transactions: int
    real_sol: float


class _BehaviorSignalOptional(TypedDict, total=False):
    lookalikes: List[LookalikePair]


class BehaviorSignal(_BehaviorSignalOptional):
    kind: str
    title: str
    description: str
    confidence: float
    examples: List[str]


class Behavior(TypedDict):
    wallet_age_days: Optional[int]
    transaction_count: int
    transaction_count_exact: bool
    transaction_tier: Optional[int]
    transactions_analyzed: int
    unique_counterparties: int
    active: Optional[bool]


class Activity(TypedDict):
    transfers: int
    swaps: int
    program_calls: int


Evidence = TypedDict(
    "Evidence",
    {"type": str, "description": str, "source": str, "confidence": float, "source_url": Optional[str]},
)


class Counterparty(TypedDict):
    address: str
    kind: str
    label: str
    labels: List[str]
    category: str
    entity: Optional[str]
    role: Optional[str]
    source: str
    interactions: int
    received_from: int
    sent_to: int
    last_seen: Optional[str]


class FlowParty(TypedDict):
    address: str
    entity: Optional[str]
    label: Optional[str]
    role: Optional[str]
    transactions: int
    signature: Optional[str]
    sol: float
    usd: float
    lookalike: bool


class FlowSide(TypedDict):
    wallets: int
    transactions: int
    sol: float
    usd: float
    other_tokens: int
    top: List[FlowParty]


class MoneyFlow(TypedDict):
    inbound: FlowSide
    outbound: FlowSide


class _TokenAmountOptional(TypedDict, total=False):
    nft: bool
    name: str


class TokenAmount(_TokenAmountOptional):
    mint: str
    amount: float


class ConnectionTransfer(TypedDict):
    signature: str
    time: Optional[int]
    direction: str
    sol: float
    usd: float
    tokens: List[TokenAmount]


class NftAmount(TypedDict):
    contract: str
    name: Optional[str]
    direction: str
    count: float


class _ConnectionAssetOptional(TypedDict, total=False):
    nft: bool


class ConnectionAsset(_ConnectionAssetOptional):
    mint: Optional[str]
    name: Optional[str]
    direction: str
    amount: float
    transactions: int


class _ConnectionOptional(TypedDict, total=False):
    calls: int
    relation: str
    nfts: List[NftAmount]
    assets: List[ConnectionAsset]


class Connection(_ConnectionOptional):
    address: str
    kind: str
    label: Optional[str]
    category: Optional[str]
    entity: Optional[str]
    role: Optional[str]
    sol_in: float
    usd_in: float
    transactions_in: int
    sol_out: float
    usd_out: float
    transactions_out: int
    lookalike: bool
    dust_only: bool
    transfers: List[ConnectionTransfer]


class SwapAsset(TypedDict):
    mint: Optional[str]
    symbol: Optional[str]
    amount: float


class SwapItem(TypedDict):
    signature: str
    time: Optional[int]
    sold: List[SwapAsset]
    bought: List[SwapAsset]


class SwapVenue(TypedDict):
    program: str
    name: Optional[str]
    swaps: int
    sold: List[SwapAsset]
    bought: List[SwapAsset]
    recent: List[SwapItem]


class Balance(TypedDict):
    sol: float
    sol_usd: Optional[float]
    tokens: int
    tokens_usd: float
    unpriced_tokens: int


class BalancePoint(TypedDict):
    time: int
    sol: float
    sampled: bool


class NftCollection(TypedDict):
    contract: str
    name: Optional[str]
    received: float
    sent: float
    minted: float
    burned: float


class ProgramParty(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    role: Optional[str]


class ProgramOwner(TypedDict):
    loader: str
    upgradeable: bool
    authority: Optional[ProgramParty]
    deployer: Optional[ProgramParty]
    deployed_at: Optional[str]
    last_deployed_at: Optional[str]
    program_data: Optional[str]


class ProgramCaller(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    role: Optional[str]
    calls: int
    failed: int
    share: float
    last_seen: Optional[str]


class ProgramAlongside(TypedDict):
    program: str
    label: Optional[str]
    entity: Optional[str]
    calls: int


class ProgramActivityPoint(TypedDict):
    time: str
    calls: int


ProgramStats = TypedDict(
    "ProgramStats",
    {
        "owner": ProgramOwner,
        "calls_analyzed": int,
        "callers": int,
        "failed": int,
        "from": Optional[str],
        "to": Optional[str],
        "top_callers": List[ProgramCaller],
        "alongside": List[ProgramAlongside],
        "activity": List[ProgramActivityPoint],
        "bucket_seconds": int,
    },
)

BundleSignal = Literal[
    "shared_signer", "jito_bundle", "same_batch", "same_setup", "shared_blockhash", "same_funder",
    "synced_sells", "funding_burst", "same_payout", "funded_by_creator", "funded_by_buyer",
    "signed_with_dev", "signed_together", "cashed_out_with_dev", "same_cashout", "proxima", "tip_spray",
    "proxima_fee", "proxima_funding", "launch_blockhash", "blockx_funding", "nonce_cashout", "blockx_fee",
    "marketplace_wallet", "same_contract", "behind_creation", "kit_sibling", "kit_creation_blockhash",
    "kit_shared_funder", "creation_block", "first_slots", "same_block", "fresh", "similar_size",
]


class _TraderOptional(TypedDict, total=False):
    signals: List[str]
    after: str
    launch_share: float
    bought_share: float
    sold_share: float
    first_buy_at: str
    last_sell_at: str


class Trader(_TraderOptional):
    address: str
    label: Optional[str]
    entity: Optional[str]
    role: Optional[str]
    relation: Optional[str]
    buys: int
    sells: int
    bought: float
    sold: float
    spent_sol: float
    received_sol: float
    spent_usd: float
    received_usd: float
    pnl_sol: float
    funded_by: Optional[str]
    fresh: bool
    holds: Optional[float]
    last_seen: Optional[str]


class TraderGroup(TypedDict):
    key: str
    """One of creator, bundlers, insiders, handed, snipers..."""
    name: str
    singular: str
    description: str
    wallets: int
    volume_sol: float
    bought_share: float
    sold_share: float
    held_share: float
    pnl_sol: float
    members: List[Trader]


class TokenFlag(TypedDict):
    severity: str
    title: str
    detail: str


class Holder(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    amount: float
    share: float
    pool: bool


class TokenLaunch(TypedDict):
    creator: Optional[str]
    created_at: Optional[str]
    creator_bought: float
    creator_sold: float
    bundles: int
    snipers: int


class BundleFunding(TypedDict):
    funder: str
    service: Optional[str]
    wallets: int
    span_secs: int
    sol: float


class ProximaBundle(TypedDict):
    wallets: int
    with_dev: bool
    signed: int
    signed_with_dev: int
    receipts: int
    sell_fees: int
    funded: int
    cashed_out_with_dev: int
    cashout: Optional[str]
    others: int


class BlockxBundle(TypedDict):
    wallets: int
    with_dev: bool
    signed_with_dev: int
    funded: int
    staging: Optional[str]
    staging_with_dev: bool
    cashed_out_with_dev: int
    cashout: Optional[str]
    fees: int
    marketplace: int
    others: int


class OwnTrades(TypedDict):
    wallets: int
    buys: int
    sells: int
    spent_sol: float
    received_sol: float
    proxima_fees_sol: float
    pnl_sol: float
    launch_bought: float
    launch_share: float
    supply_base: str
    complete: bool


class _BundleHubOptional(TypedDict, total=False):
    amounts: List[Optional[float]]
    service: str
    with_dev: bool


class BundleHub(_BundleHubOptional):
    address: str
    kind: Literal["funder", "contract", "cashout", "signer", "creator"]
    members: List[str]


class _TokenBundleOptional(TypedDict, total=False):
    own_trades: OwnTrades
    hubs: List[BundleHub]


class TokenBundle(_TokenBundleOptional):
    wallets: int
    spent_sol: float
    bought_share: float
    sold_share: float
    held_share: float
    launch_share: float
    blocks: int
    first_buy_at: Optional[str]
    after_launch_secs: Optional[int]
    clusters: int
    signals: Dict[str, int]
    funding: Optional[BundleFunding]
    proxima: Optional[ProximaBundle]
    blockx: Optional[BlockxBundle]
    kit: int
    summary: str


class Layout(TypedDict):
    kind: Literal["proxima", "blockx", "unknown", "direct"]
    label: str
    reasons: List[str]


class _CheckLineOptional(TypedDict, total=False):
    ok: bool
    layout: Layout


class CheckLine(_CheckLineOptional):
    label: str
    text: str
    signatures: List[str]


class DevFeeWallet(TypedDict):
    address: str
    sol: float
    mints: List[str]
    sell_fees: int
    claim_cuts: int


class FundingBurst(TypedDict):
    senders: int
    sol_each: float
    span_secs: int
    before_launch_secs: Optional[int]
    examples: List[str]
    burst: bool
    funding_tips: List[str]
    tipped_funding: Optional[str]
    funder: Optional[str]
    stake_bounce: Optional[str]
    nonce_bounce: Optional[str]
    proxima_like: bool
    layout: Layout


class LaunchTips(TypedDict):
    relays: List[str]
    tip_transactions: List[str]
    proxima_like: bool


class BlockxFunding(TypedDict):
    funder: Optional[str]
    relay: Optional[str]
    sol: float
    nonce_hop: bool
    recipe: bool
    marketplace_funder: Optional[str]
    marketplace_sweep: Optional[str]
    blockx_like: bool
    signatures: List[str]
    layout: Layout


class BlockxCheck(TypedDict):
    made_with: bool
    funding: Optional[BlockxFunding]
    fees: int
    fee_sol: float
    rate: Optional[float]
    fee_wallet: Optional[str]
    flat_fees: int
    fee_signatures: List[str]
    cashouts: int
    cashout_sol: float
    cashout_to: Optional[str]
    cashout_signatures: List[str]
    rent_reclaims: int
    launch_shape: bool
    global_fee: Optional[str]
    summary: str


KitVerdict = Literal["proxima", "blockx", "launch_kit", "funded_like_kit", "none"]


class KitLayer(TypedDict):
    to: str
    lamports: int
    senders: List[str]
    payments: int
    start: int
    end: int
    signatures: List[str]


class KitTreeLevel(TypedDict):
    level: int
    wallets: int
    read: int
    layers: int
    largest: Optional[str]
    signatures: List[str]


class KitTree(TypedDict):
    depth: int
    wallets: int
    levels: List[KitTreeLevel]
    creator_layers: List[KitLayer]
    first_funding: Optional[int]
    reads: int
    capped: bool
    busy: int
    top: List[str]
    sibling_count: int
    siblings: List[str]


class KitMark(TypedDict):
    kind: Literal["sell_fee", "claim_cut", "receipt"]
    who: str
    wallet: str
    signature: str
    sol: float
    base_sol: Optional[float]
    fee_wallet: Optional[str]
    fresh_fee_wallet: Optional[bool]
    strict: bool
    counts: bool


class KitMember(TypedDict):
    address: str
    why: List[str]
    sol: float
    share: float
    after: str
    funder: Optional[str]


class KitBundle(TypedDict):
    wallets: int
    sol: float
    share: float
    siblings: int
    creation_blockhash: int
    shared_funder: int
    sold: int
    holding: int
    sent_on: int
    members: List[KitMember]


class LaunchKit(TypedDict):
    verdict: KitVerdict
    title: Optional[str]
    tree: Optional[KitTree]
    funded_and_tipped: bool
    bundle: Optional[KitBundle]
    marks: List[KitMark]
    summary: str


class DevCheck(TypedDict):
    """Whether a launch kit made a token (``token["launch_tool"]`` in /analyze)."""

    tool: str
    checked: List[str]
    creator: str
    made_with: bool
    proxima: bool
    funding: Optional[FundingBurst]
    tipping: Optional[LaunchTips]
    sell_fees: int
    claim_cuts: int
    receipts: int
    fee_wallets: List[DevFeeWallet]
    blockx: Optional[BlockxCheck]
    lines: List[CheckLine]
    summary: str
    verdict: KitVerdict
    funded_and_tipped: bool
    tree: Optional[KitTree]
    launch_kit: Optional[LaunchKit]
    checked_at: int
    creator_latest: Optional[str]


class FreshBuyer(TypedDict):
    address: str
    sol: float
    tokens: float
    share: float
    funder: Optional[str]
    funder_name: Optional[str]
    funder_sol: Optional[float]


class FreshBuyers(TypedDict):
    checked: int
    unknown: int
    wallets: int
    sol: float
    share: float
    buyers: List[FreshBuyer]
    severity: str
    summary: str


class TradePoint(TypedDict):
    time: str
    buys: int
    sells: int
    volume_sol: float


class Distributor(TypedDict):
    address: str
    sent: float
    share: float
    recipients: int
    from_creator: bool
    first: Optional[str]
    last: Optional[str]


Handout = TypedDict(
    "Handout",
    {"from": str, "to": str, "amount": float, "share": float, "signature": str, "time": Optional[str]},
)

Acquisition = TypedDict(
    "Acquisition",
    {
        "address": str,
        "share": float,
        "how": str,
        "from": Optional[str],
        "handed": float,
        "signature": Optional[str],
        "time": Optional[str],
    },
)


class Distribution(TypedDict):
    transfers: int
    tokens: float
    share: float
    recipients: int
    creator_wallets: int
    creator_share: float
    distributors: List[Distributor]
    handouts: List[Handout]
    holders: List[Acquisition]


class PastToken(TypedDict):
    mint: str
    symbol: Optional[str]
    launcher: str
    via: str
    launched_at: Optional[str]
    last_active_at: Optional[str]
    life_secs: Optional[int]
    status: str
    launcher_got: float
    launcher_sold: float
    launcher_pnl_sol: float
    sold_out: bool


class TrackRecord(TypedDict):
    creator: str
    funder: Optional[str]
    funder_note: Optional[str]
    creator_txs: int
    creator_whole: bool
    siblings_checked: int
    launchers: int
    launched: int
    checked: int
    died_young: int
    faded: int
    alive: int
    sold_out: int
    pnl_sol: float
    median_life_secs: Optional[int]
    tokens: List[PastToken]
    complete: bool
    summary: str


class _PricePointOptional(TypedDict, total=False):
    price_usd: float
    mcap_usd: float


class PricePoint(_PricePointOptional):
    time: int
    price: float
    mcap: Optional[float]
    trades: int


class TradeMark(TypedDict):
    time: int
    signature: str
    wallet: str
    role: str
    side: str
    tokens: float
    sol: float
    price: Optional[float]


Tick = Tuple[int, float, float, int]
"""One trade: (unix seconds, price, tokens, side)."""

PriceGap = TypedDict("PriceGap", {"from": int, "to": int})

_TokenStatsBase = TypedDict(
    "_TokenStatsBase",
    {
        "mint": str,
        "name": Optional[str],
        "symbol": Optional[str],
        "image": Optional[str],
        "program": str,
        "decimals": int,
        "supply": float,
        "mint_authority": Optional[str],
        "freeze_authority": Optional[str],
        "pump_fun": bool,
        "graduated": bool,
        "launch": Optional[TokenLaunch],
        "bundle": Optional[TokenBundle],
        "launch_tool": Optional[DevCheck],
        "trades_analyzed": int,
        "traders": int,
        "buys": int,
        "sells": int,
        "volume_sol": float,
        "from": Optional[str],
        "to": Optional[str],
        "groups": List[TraderGroup],
        "flags": List[TokenFlag],
        "creator_funder": Optional[str],
        "creator_funding_layout": Optional[Layout],
        "holders": List[Holder],
        "activity": List[TradePoint],
        "bucket_seconds": int,
        "distribution": Distribution,
        "track_record": Optional[TrackRecord],
        "price": List[PricePoint],
        "price_bucket_seconds": int,
        "price_gap": Optional[PriceGap],
        "ticks": List[Tick],
        "marks": List[TradeMark],
    },
)


class _TokenStatsOptional(TypedDict, total=False):
    launchpad: str
    quote: str
    fresh_buyers: FreshBuyers
    gap_ticks: List[Tick]
    native_usd: List[Tuple[int, float]]
    story: Dict[str, Any]


class TokenStats(_TokenStatsBase, _TokenStatsOptional):
    """A token's report (``token`` in /analyze for a mint)."""


class AnalyzeMeta(TypedDict):
    analyzed_at: str
    data_completeness: float
    scope: Literal["live", "database"]
    warning: Optional[str]
    depth: int
    free: bool


class _AnalyzeResultOptional(TypedDict, total=False):
    program: ProgramStats
    token: TokenStats
    nfts: List[NftCollection]


class AnalyzeResult(_AnalyzeResultOptional):
    """``POST /analyze``: who an address is, how risky, the evidence, its money in and out."""

    address: str
    chain: str
    native_symbol: str
    identity: Identity
    risk: Risk
    summary: List[str]
    labels: List[Label]
    behaviors: List[BehaviorSignal]
    behavior: Behavior
    activity: Activity
    evidence: List[Evidence]
    flagged_counterparties: List[Counterparty]
    known_counterparties: List[Counterparty]
    flows: MoneyFlow
    connections: List[Connection]
    swap_venues: List[SwapVenue]
    balance: Optional[Balance]
    balance_history: List[BalancePoint]
    meta: AnalyzeMeta


# ------------------------------------------------------------------------------------------------
# POST /insiders
# ------------------------------------------------------------------------------------------------

InsiderLink = Literal["funded_by_dev", "sent_to_dev", "same_funder", "dev_funded_funder"]

InsiderHop = TypedDict(
    "InsiderHop",
    {
        "from": str,
        "to": str,
        "signature": Optional[str],
        "time": Optional[str],
        "what": str,
        "sol": float,
        "tokens": float,
        "usd": float,
    },
)


class Insider(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    link: InsiderLink
    link_name: str
    confidence: float
    path: List[InsiderHop]
    through: Optional[str]
    also: List[InsiderLink]
    via: Optional[str]
    reasons: List[str]
    fresh: bool
    first_buy_seconds: Optional[int]
    first_buy_at: Optional[str]
    bundled: bool
    """Bought in the launch block."""
    bought: float
    spent_sol: float
    spent_usd: float
    received: float
    holds: Optional[float]
    """Share of the supply it holds now, 0 to 1, when it could be read."""


class InsiderDev(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    funded_by: List[InsiderHop]
    funded_from: Optional[str]
    via: Optional[str]
    fresh: bool


class InsidersSummary(TypedDict):
    insiders: int
    held_share: float
    bought_share: float
    candidates: int
    checked: int
    by_link: Dict[str, int]


class InsidersResult(TypedDict):
    """``POST /insiders``: the wallets a token's creator is linked to by money."""

    mint: str
    chain: str
    name: Optional[str]
    symbol: Optional[str]
    supply: float
    launched_at: Optional[str]
    dev: InsiderDev
    limit: int
    depth: int
    complete: bool
    insiders: List[Insider]
    summary: InsidersSummary
    notes: List[str]


# ------------------------------------------------------------------------------------------------
# POST /launch-tool
# ------------------------------------------------------------------------------------------------


class LaunchToolEvidence(TypedDict):
    kind: str
    strength: Literal["strong", "moderate", "weak"]
    text: str
    signatures: List[str]


class LaunchedToken(TypedDict):
    mint: str
    name: Optional[str]
    symbol: Optional[str]
    time: Optional[str]
    signature: str
    relays: List[str]
    tip_signatures: List[str]


class SellFee(TypedDict):
    signature: str
    sell_signature: str
    time: Optional[str]
    mint: Optional[str]
    fee_wallet: str
    sol_received: float
    fee_sol: float
    with_sell: bool
    slot_gap: Optional[int]


class Sells(TypedDict):
    seen: int
    through_tool: int
    sol_received: float
    fees_sol: float
    unconfirmed: int
    fees: List[SellFee]


class FeeWalletPayment(TypedDict):
    to: str
    label: Optional[str]
    entity: Optional[str]
    sol: float
    mint: Optional[str]
    amount: float
    signature: str
    time: Optional[str]


class FeeWallet(TypedDict):
    address: str
    mints: List[str]
    paid_sol: float
    sell_fees: int
    claim_cuts: int
    trade_fees: int
    first_paid: Optional[str]
    balance_sol: Optional[float]
    transactions: Optional[int]
    more_transactions: bool
    swept: Optional[bool]
    sent: List[FeeWalletPayment]


class CreatorFeeClaim(TypedDict):
    signature: str
    time: Optional[str]
    venue: str
    claimed_sol: float
    cut_sol: float
    fee_wallet: str
    mint: Optional[str]
    vault: Optional[str]
    tips: List[str]


class FundingLayer(TypedDict):
    depth: int
    wallets: int
    read: int
    transfers: int
    amount_sol: Optional[float]
    same_amount: int
    fan_out: Optional[int]
    first: Optional[str]
    last: Optional[str]
    examples: List[str]


class FundingStop(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    reason: str
    depth: int
    transfers: int
    sol: float


class FundingRoot(TypedDict):
    address: str
    label: Optional[str]
    entity: Optional[str]
    depth: int
    reason: str
    transfers: int
    sol: float
    first_funder: Optional[str]
    first_funder_label: Optional[str]
    first_funder_entity: Optional[str]
    first_funding_sol: Optional[float]
    first_funding_signature: Optional[str]
    fresh: Optional[bool]


class FundingTree(TypedDict):
    layers: List[FundingLayer]
    wallets: int
    transfers: int
    first: Optional[str]
    last: Optional[str]
    span_seconds: Optional[int]
    tree: bool
    layout: Layout
    root: Optional[FundingRoot]
    stops: List[FundingStop]
    complete: bool


class ScanWindow(TypedDict):
    transactions: int
    oldest: Optional[str]
    newest: Optional[str]
    whole_history: bool


class LaunchToolResult(TypedDict):
    """``POST /launch-tool``. ``tool``/``tool_name`` are named even when nothing was found: read ``verdict``."""

    wallet: str
    mint: Optional[str]
    from_mint: Optional[str]
    tool: Literal["proxima", "blockx"]
    tool_name: str
    tool_site: str
    checked: List[str]
    verdict: Literal["tool", "likely", "none"]
    verdict_name: str
    confidence: float
    evidence: List[LaunchToolEvidence]
    tokens_launched: List[LaunchedToken]
    sells: Sells
    fee_wallets: List[FeeWallet]
    claims: List[CreatorFeeClaim]
    funding: Optional[FundingTree]
    window: ScanWindow
    requests: int
    complete: bool
    notes: List[str]


# ------------------------------------------------------------------------------------------------
# POST /follow
# ------------------------------------------------------------------------------------------------


class FollowAsset(TypedDict):
    symbol: str
    address: Optional[str]
    decimals: int


class FollowLabel(TypedDict):
    name: str
    kind: str


FollowHop = TypedDict(
    "FollowHop",
    {
        "from": str,
        "to": str,
        "amount": float,
        "usd": Optional[float],
        "symbol": str,
        "signature": str,
        "time": Optional[int],
        "share": float,
        "to_label": Optional[FollowLabel],
    },
)


class FollowBranch(TypedDict):
    to: str
    amount: float
    usd: Optional[float]
    signature: str
    to_label: Optional[FollowLabel]


class FollowEnd(TypedDict):
    reason: str
    """exchange, bridge, mixer, dex_swap, split, at_rest, loop, max_hops or no_data."""
    address: str
    detail: str
    holding: Optional[float]
    branches: List[FollowBranch]
    output: Optional[FollowAsset]
    signature: Optional[str]
    time: Optional[int]


class _FollowResultOptional(TypedDict, total=False):
    credits: Credits


class FollowResult(_FollowResultOptional):
    """``POST /follow``: the main stream of money out of a wallet, hop by hop."""

    chain: str
    start: str
    asset: FollowAsset
    hops: List[FollowHop]
    end: FollowEnd


# ------------------------------------------------------------------------------------------------
# POST /trace
# ------------------------------------------------------------------------------------------------


class TraceAnchor(TypedDict):
    signature: str
    amount: float
    asset: str
    time: int


TraceWindow = TypedDict(
    "TraceWindow",
    {
        "from": int,
        "to": int,
        "searched": List[str],
        "transactions": int,
        "complete": bool,
        "truncated": bool,
        "open": bool,
        "closes_at": Optional[int],
        "fallback": bool,
    },
)


class TraceSplitPart(TypedDict):
    signature: str
    address: str
    amount: float
    time: int


TraceSplit = TypedDict("TraceSplit", {"group": int, "parts": int, "with": List[TraceSplitPart]})


class TracePart(TypedDict):
    signature: str
    amount: float
    time: int


class _TraceCandidateOptional(TypedDict, total=False):
    asset: str
    usd: float
    chain: str
    reason: str
    fee: float
    split: TraceSplit
    reasons: List[str]
    parts: List[TracePart]


class TraceCandidate(_TraceCandidateOptional):
    address: str
    signature: str
    amount: float
    time: int
    delta_seconds: int
    tier: str
    confidence: float
    via: Optional[str]
    label: Optional[str]
    same_wallet: bool


class SwapLeg(TypedDict):
    coin: str
    network: str
    amount: Optional[float]
    usd: Optional[float]
    time: Optional[int]


class TraceSwap(TypedDict):
    service: str
    matched: str
    deposit: SwapLeg
    settle: Optional[SwapLeg]
    recorded_at: Optional[int]
    other_chain: bool
    priced: bool
    shifts: int


class TraceCluster(TypedDict):
    relayer: Optional[str]
    transactions: int
    addresses: List[str]
    address_count: int
    mix: List[str]
    amount: float
    overlap: float
    first: int
    last: int
    fresh: Optional[int]
    confidence: float
    reasons: List[str]
    signatures: List[str]


class _TraceResultOptional(TypedDict, total=False):
    swap: TraceSwap
    chain: str
    clusters: List[TraceCluster]


class TraceResult(_TraceResultOptional):
    """``POST /trace``: the likely wallets on the other side of a mixer, exchange or swap service."""

    entity: str
    kind: str
    direction: Literal["forward", "backward"]
    method: str
    anchor: TraceAnchor
    window: TraceWindow
    anonymity_set: int
    candidates: List[TraceCandidate]
    warnings: List[str]


# ------------------------------------------------------------------------------------------------
# POST /tx, /xchain/*
# ------------------------------------------------------------------------------------------------


class BridgeLeg(TypedDict):
    chain: str
    chain_name: str
    address: Optional[str]
    tx: Optional[str]
    tx_url: Optional[str]
    address_url: Optional[str]
    time: Optional[int]
    amount: Optional[float]
    asset: Optional[str]
    analyzable: bool


class BridgeLink(TypedDict):
    bridge: str
    protocol: Optional[str]
    status: Literal["completed", "pending", "refunded", "unclaimed", "failed"]
    direction: Literal["out", "in"]
    source: BridgeLeg
    destination: Optional[BridgeLeg]
    hops: List[BridgeLeg]
    explorer_url: Optional[str]
    evidence: str


class XchainResult(TypedDict):
    """``POST /xchain/resolve`` and ``/xchain/wallet``: bridge transfers, both ends of each."""

    links: List[BridgeLink]
    warnings: List[str]


TxTransfer = TypedDict(
    "TxTransfer",
    {"from": str, "to": str, "amount": float, "asset": str, "mint": Optional[str], "usd": Optional[float]},
)


class TxParty(TypedDict):
    address: str
    chain: str
    kind: str
    label: Optional[str]
    category: Optional[str]
    entity: Optional[str]
    role: str
    analyzable: bool


class TxProgram(TypedDict):
    address: str
    name: Optional[str]


class TxResult(TypedDict):
    """``POST /tx``: one transaction explained."""

    chain: str
    chain_name: str
    hash: str
    url: str
    time: Optional[int]
    status: str
    fee_payer: Optional[str]
    signers: List[str]
    summary: str
    transfers: List[TxTransfer]
    parties: List[TxParty]
    programs: List[TxProgram]
    bridge: Optional[XchainResult]


# ------------------------------------------------------------------------------------------------
# POST /victims, /kind, /chains; GET /status
# ------------------------------------------------------------------------------------------------


class Victim(TypedDict):
    address: str
    sol: float
    usd: float
    tokens: int
    transactions: int
    first: Optional[str]
    last: Optional[str]
    signature: str


class VictimsResult(TypedDict):
    """``POST /victims``: a drainer's victims and what each lost."""

    address: str
    victims: int
    sol: float
    usd: float
    tokens: int
    transactions_read: int
    complete: bool
    first: Optional[str]
    last: Optional[str]
    top: List[Victim]


class KindResult(TypedDict):
    kind: Literal["token", "other"]


class ChainActivity(TypedDict):
    chain: str
    active: Optional[bool]
    sent: Optional[int]
    balance: Optional[float]
    symbol: str


class ChainsResult(TypedDict):
    address: str
    chains: List[ChainActivity]


Health = Literal["operational", "degraded", "outage", "unknown"]


class _StatusCheckOptional(TypedDict, total=False):
    error: str


class StatusCheck(_StatusCheckOptional):
    at: int
    ok: bool
    latency_ms: int


class StatusComponent(TypedDict):
    id: str
    name: str
    description: str
    status: Health
    latency_ms: Optional[int]
    uptime: Optional[float]
    checks: List[StatusCheck]
    interval_seconds: int


class StatusMinute(TypedDict):
    at: int
    requests: int
    errors: int
    avg_ms: Optional[int]


class StatusEndpoint(TypedDict):
    id: str
    name: str
    description: str
    status: Health
    requests: int
    errors: int
    avg_ms: Optional[int]
    p50_ms: Optional[int]
    p95_ms: Optional[int]
    max_ms: Optional[int]
    last_request_at: Optional[int]
    timeline: List[StatusMinute]


class StatusIncident(TypedDict):
    id: int
    component: str
    severity: str
    title: str
    message: str
    started_at: str
    resolved_at: Optional[str]


class KnowledgeBaseStatus(TypedDict):
    labels: int
    sources: int
    refresh: str


class UptimeWindow(TypedDict):
    days: int
    since: int
    uptime: float
    down_seconds: int


class ServiceUptime(TypedDict):
    id: str
    windows: List[UptimeWindow]


class StatusResult(TypedDict):
    """``GET /status``: the health of the API and what it relies on."""

    status: Health
    checked_at: int
    started_at: int
    uptime_seconds: int
    version: str
    check_interval_seconds: int
    slot: Optional[int]
    components: List[StatusComponent]
    endpoints: List[StatusEndpoint]
    knowledge_base: KnowledgeBaseStatus
    incidents: List[StatusIncident]
    uptime: List[ServiceUptime]


class RiskSummary(TypedDict):
    """``risk_summary(...)``: a few facts in one shape. ``None`` means "this call doesn't say"."""

    bundled: Optional[bool]
    bundle_held_pct: Optional[float]
    dev_sold: Optional[bool]
    dev_held_pct: Optional[float]
    launch_tool: Optional[str]
    risk_score: Optional[float]
    notes: List[str]


AnyResult = Union[AnalyzeResult, InsidersResult, LaunchToolResult]
