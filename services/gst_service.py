def calculate_gst(price,quantity,gst_percent):
    try:
        subtotal=price*quantity

        gst_amount=subtotal*(gst_percent/100)

        total=subtotal+gst_amount

        return{
            "subtotal":round(subtotal,2),
            "gst_amount":round(gst_amount,2),
            "total":round(total,2)
        }
    
    except Exception as e:
        print("Error in calculate_gst:", e)
        return None