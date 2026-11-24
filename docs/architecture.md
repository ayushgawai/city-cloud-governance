# Architecture notes

## Why two implementations of the same policy?

The Terraform modules are what you would actually apply. The Python package
mirrors their decisions — permission-boundary denials, required tags, GovCloud
region allowlist, RightSize thresholds, storage tiers, OLS forecast — so the
*logic* can be unit-tested and benchmarked offline in seconds, with no AWS
account. If the two disagree, the Python tests are the specification and the
HCL should be fixed to match.

## Governance flow

1. Organizations SCPs / tag policies prevent what the boundary does not.
2. Every role carries `city-permission-boundary`; the boundary hard-denies
   tampering with CloudTrail, Config, and Organizations membership.
3. Config rules detect drift that prevention missed; `citygov plan` reproduces
   that detection over an exported inventory (the fixture tree here).
4. Budgets + forecast alerts close the cost loop; RightSize and storage-tier
   recommendations are generated from utilisation, not guesses.

## Scaling note

The fixture tree is 12 flat JSON files on purpose. A real deployment would
replace `load_tree()` with a Config aggregator / Security Hub export — the
policy, cost, and scoring functions already take plain dicts, so only the
loader changes.
