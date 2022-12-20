# Change Log

## 2.0.0

### Added

* Added Tinyman V2 support (`tinyman.v2`).
* Added Staking support (`tinyman.staking`).
  - It allows creating commitment transaction by `prepare_commit_transaction` and tracking commitments by `parse_commit_transaction`.
* Added `calculate_price_impact` function to `tinyman.utils`.
* Improved `TransactionGroup` class.
  - Added `+` operator support for composability, it allows creating a new transaction group (`txn_group_1 + txn_group_2`).
  - Added `id` property, it returns the transactions group id.
  - Added `TransactionGroup.sign_with_logicsig` function and deprecated `TransactionGroup.sign_with_logicisg` because of the typo.

### Changed

* `get_program` (V1) is moved from `tinyman.utils` to `tinyman.v1.contracts`.
* `get_state_from_account_info` (V1) is moved from `tinyman.utils` to `tinyman.v1.utils`.

### Removed

* Deprecated `wait_for_confirmation` function is removed. `wait_for_confirmation` is added to [Algorand SDK](https://github.com/algorand/py-algorand-sdk).
* Drop Python 3.7 support.

