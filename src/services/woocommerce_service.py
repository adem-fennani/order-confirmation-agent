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
