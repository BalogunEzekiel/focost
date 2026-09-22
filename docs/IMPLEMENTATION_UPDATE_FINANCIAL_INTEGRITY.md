# FOCOST Financial Integrity Update

## Scope

This update strengthens goal-contribution and investment accounting while preserving the existing FOCOST architecture and DashboardService as the dashboard financial source of truth.

## Goals

- Contributions cannot exceed the remaining target.
- Completed goals reject additional contributions.
- Goal target amounts cannot be reduced below amounts already contributed.
- Goal contributions require sufficient available cash as of the contribution date.
- Each contribution is linked one-to-one with its expense record.
- Contribution and expense dates remain synchronized when a contribution is edited.
- Future-dated goals are never labelled `Behind` solely because their funding percentage is low.
- Future-dated goals do not generate a `Goal Behind Schedule` notification through the guarded notification helper.

## Investments

- Investment creation originates from Assets & Investments rather than the generic Expense form.
- Funding creates a linked `investment` expense and an investment asset.
- Funding is rejected when sufficient available cash is not present as of the investment date.
- Investment valuation changes create dated `valuation` events and corresponding investment gain/loss income/expense records.
- Valuation gains/losses are non-cash accounting events and therefore do not increase or reduce spendable cash until liquidation.
- Investments cannot be deleted; they can be partially or fully liquidated.
- Liquidation preserves the investment record and creates dated cash proceeds classified as `investment_liquidation`.
- Investment event history records funding, valuation and liquidation details.

## Financial reporting

The report dataset now exposes separate values for:

- goal contributions;
- investment funding;
- investment gains;
- investment losses;
- liquidation proceeds;
- active investment cost basis; and
- active investment current value/gain-loss.

Expenses used for financial cash-flow reporting include linked goal contributions, investment funding and investment valuation losses, while the dashboard's budget/spending analysis continues to distinguish ordinary operating expenses where appropriate.

## Source-of-origin protection

Investment- and goal-originated transactions cannot be directly edited, deleted or reclassified from the general Income/Expenses interfaces. Users are directed to the originating Goals or Investments workflow.

## Database integrity

Migration `3c9e7a1b5d2f` adds:

- `income.transaction_class`;
- `investment_events` audit/history table; and
- positive/non-negative database checks for financial amounts.

Cross-row rules such as the aggregate goal cap and available-cash requirement remain enforced in application/business logic because they depend on related records.

## Validation

Python AST/syntax validation was run across the application Python source and the new integrity tests. Full pytest execution requires the project's Python dependencies to be installed in the execution environment.
