# Фрагмент сдачи; окружение Django не предоставлено.
with transaction.atomic():
    product = Product.objects.get(pk=sku)
    if product.stock < qty:
        raise OutOfStock()
    product.stock -= qty
    product.save()
