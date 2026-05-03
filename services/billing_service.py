from services.gst_service import calculate_gst

def calculate_bill(cart_items):
    try:
        bill_item=[]
        subtotal=0
        total_gst=0
        grand_total=0

        for item in cart_items:
            price=float(item["price"])
            quantity=int(item["quantity"])
            gst_percent=float(item["gst_percent"])

            if item["quantity"] <= 0:
                return None
            

            gst_data=calculate_gst(price,quantity,gst_percent)

            line_item = {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": quantity,
                    "unit_price": price,
                    "gst_percent": gst_percent,
                    "subtotal": gst_data["subtotal"],
                    "gst_amount": gst_data["gst_amount"],
                    "line_total": gst_data["total"]
                }
            
            bill_item.append(line_item)

            subtotal+=gst_data["subtotal"]
            total_gst+=gst_data["gst_amount"]
            grand_total+=gst_data["total"]

        return{
                "items":bill_item,
                "subtotal":subtotal,
                "total_gst":total_gst,
                "total_amount":grand_total
            }
    
    except Exception as e:
        print("Error in calculate_bill:", e)
        return None


