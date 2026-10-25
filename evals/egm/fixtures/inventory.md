# Inventory deletion packet P7

Owner-acknowledged design: remove unsold drafts while preserving purchase history.
- A1: A product referenced by any order cannot be deleted. Return 409; product and order rows remain unchanged.
- A2: Only the owning shop may delete its own unsold product. Another shop receives 403 and no rows change.
- A3: An owned unsold product can be deleted; return 204.

Approved change D8: rename product.shop_id to product.owner_id in this candidate.
No behavior change was authorized. This supersedes the old field name, not A1-A3.
Candidate source: delete_product.py. Persistence removes the product when delete_product is called.
orders.count_for_product returns the number of referencing orders.
The fixture omits actual storage and tests. Reported tests cover only owned unsold deletion.
No gate-two review, production journey, or merge acknowledgment has been completed for this candidate.
