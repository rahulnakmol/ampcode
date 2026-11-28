def remove_product(actor, product, orders, store):
    if actor.shop_id != product.owner_id:
        return 403
    order_count = orders.count_for_product(product.id)
    store.delete_product(product.id)
    return 204
