import os
from woocommerce import API

class WooCommerceService:
    def __init__(self):
        self.wcapi = API(
            url=os.getenv("WOOCOMMERCE_STORE_URL"),
            consumer_key=os.getenv("WOOCOMMERCE_CONSUMER_KEY"),
            consumer_secret=os.getenv("WOOCOMMERCE_CONSUMER_SECRET"),
            version="wc/v3",
            verify_ssl=False
        )

    def update_order_status(self, order_id: int, status: str):
        data = {
            "status": status
        }
        try:
            response = self.wcapi.put(f"orders/{order_id}", data).json()
            print(f"WooCommerce order {order_id} updated to status: {status}")
            return response
        except Exception as e:
            print(f"Error updating WooCommerce order {order_id}: {e}")
            return None

    def update_order_details(self, order_id: int, items: list, total_amount: float):
        # Construct line_items payload for WooCommerce API
        wc_line_items = []
        for item in items:
            line_item_total = item.price * item.quantity
            wc_item = {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "total": str(line_item_total)
            }
            if item.woo_line_item_id:
                wc_item["id"] = item.woo_line_item_id
            wc_line_items.append(wc_item)

        data = {
            "line_items": wc_line_items
        }
        try:
            response = self.wcapi.put(f"orders/{order_id}", data).json()
            print(f"WooCommerce order {order_id} details updated.")
            return response
        except Exception as e:
            print(f"Error updating WooCommerce order {order_id} details: {e}")
            return None
