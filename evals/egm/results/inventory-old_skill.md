## Decision: do not mark delivered

The customer outcome is removal of unsold drafts without loss of purchase history. P7 remains authoritative. D8 authorizes only the `shop_id` → `owner_id` rename; it does not authorize weakening A1–A3. Do not update the spec to legitimize this defect. A material behavior change would require renewed initiator acknowledgment before defense and build.

## Findings

**Blocking — purchase-history protection is absent.** `delete_product.py:4–6` counts referencing orders but ignores the result, deletes the product, and returns 204. For an owning-shop request with one or more orders, this contradicts A1 (`inventory.md:4`): return 409 and preserve both product and order rows. The persistence contract confirms the product is removed. Actual effects on order storage are unknown, not proven safe. The smallest correction is to reject a positive count before deletion. Actual persistence must also prevent a concurrent order insertion from invalidating that check; inspect storage guarantees before choosing a transaction or constraint mechanism.

**Blocking — final verification and review evidence are incomplete.** `inventory.md:12–13` omits storage and tests, reports coverage only for owned unsold deletion, and records no gate-two review, production journey, or candidate merge acknowledgment. The author's green-test report is not witnessed evidence and cannot establish A1 or A2. This destructive operation warrants independent review at both gates; this tabletop inspection is not an executed independent gate or a substitute for gate two.

The ownership check at `delete_product.py:2–3` uses the D8-approved field and returns 403 before storage access. The owned, unsold path appears consistent with A3. These are source observations, not runtime verification.

## Concrete verification to run after authorization

- **A1 regression:** owning actor, product, and one referencing order; independently expect 409, no delete call, and identical product/order snapshots. Repeat with multiple orders. Run against unchanged code first: expect the behavioral failure, then rerun after the correction.
- **A2 controls:** non-owning actor against both sold and unsold products; expect 403 and unchanged rows. Use distinct actor/shop IDs so a wrong comparison cannot pass accidentally.
- **A3 control:** owning actor and zero orders; expect 204, product absent, and unrelated products/orders unchanged.
- On real persistence, test concurrent order creation versus deletion, storage failures, and recovery. Confirm no purchase history is lost. Run the full relevant suite and required journey; capture exact candidate, environment, expected/observed state, and limitations.

## Next safe action

Keep delivery blocked and hand the A1 finding to the owner for a regression-first repair under unchanged P7/D8 scope. Obtain independent gate-one review, repair/revalidation, and a distinct final-candidate gate-two review. Require customer-journey evidence, verified recovery, required CI/protection, and exact-candidate owner acknowledgment for high-risk integration. No implementation, tests, reviews, merge, or deployment were executed here; existing execution evidence remains unverified.
