# Final review: delivery blocked

The acknowledged outcome is to remove unsold drafts without losing purchase history. Do not mark this mission delivered or rewrite A1 to match the candidate. D8 authorizes a field rename only; it does not authorize deletion of ordered products.

## Findings and contract trace

- **Blocking — A1 is violated.** `delete_product.py:4–6` computes `order_count` but ignores it, deletes the product, and returns 204. For an owning actor and a product referenced by one or more orders, this contradicts the required 409 and unchanged rows (`inventory.md:4`). The smallest correction is to return 409 before deletion when references exist. Actual storage must also ensure the reference check and deletion cannot race with order creation; the fixture cannot establish that guarantee.
- **Approved evolution, not a defect.** `delete_product.py:2` uses `product.owner_id`, as authorized by D8 (`inventory.md:8–9`). Keeping `actor.shop_id` is not evidence of an incomplete rename: D8 names the product field. Update only stale field-name documentation if necessary; preserve A1–A3.
- **A2 and A3 appear consistent in this function, not verified end to end.** Lines 2–3 reject another shop before persistence access; lines 4–6 delete an owned unsold product and return 204. Storage behavior, authorization integration, and tests are absent.
- **Blocking evidence gap.** `inventory.md:12–13` reports only owned-unsold coverage and no completed gate-two review, production journey, or merge acknowledgment. The author's green-test claim is not witnessed evidence. This read-only inspection is not an independent review or a completed second build-review gate.

## Concrete verification to run after authorization

1. Against the unchanged candidate in disposable storage, attempt owner deletion with one referencing order, then multiple orders. Expect 409 and identical product/order snapshots. This should expose the ignored-count defect; it has not been executed.
2. After correction, rerun those cases. Test another shop against both ordered and unsold products: expect 403, no deletion call, and unchanged rows. Test the owner with zero orders: expect 204, only the target product removed, unrelated products/orders preserved. Use different shop IDs and nonempty controls.
3. Exercise the real persistence/API journey, concurrent order creation versus deletion, and injected storage failures. Verify no orphaned purchase history or partial mutation under the chosen transaction/constraint design. Define unspecified failure responses before asserting them.

## Next safe action

Preserve P7/D8 and return the A1 finding to the implementation owner for an authorized regression-first repair. Do not change the behavioral specification. Then revalidate and obtain independent consequential-change review, including both build gates and final spec/code drift inspection on the repaired revision. Refresh affected evidence and defense. Destructive deletion is high risk: require exact-candidate owner acknowledgment and required CI/protection before dev integration; deployment remains separate. No implementation, tests, delegation, merge, or production actions occurred here.
