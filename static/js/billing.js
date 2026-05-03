let cart = [];

/* Add product to cart */
function addToCart(card) {
    const id = parseInt(card.dataset.id);
    const name = card.dataset.name;
    const price = parseFloat(card.dataset.price);
    const gst = parseFloat(card.dataset.gst);

    const existing = cart.find(item => item.product_id === id);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            product_id: id,
            product_name: name,
            price: price,
            gst_percent: gst,
            quantity: 1
        });
    }

    renderCart();
}

/* Render cart UI */
function renderCart() {
    const cartBox = document.getElementById("cart-items");

    cartBox.innerHTML = "";

    let subtotal = 0;
    let gstTotal = 0;

    cart.forEach(item => {
        const lineTotal = item.price * item.quantity;
        const gstAmount = lineTotal * item.gst_percent / 100;

        subtotal += lineTotal;
        gstTotal += gstAmount;

        cartBox.innerHTML += `
            <div class="cart-row">
                <span>${item.product_name} x ${item.quantity}</span>
                <span>₹${lineTotal.toFixed(2)}</span>
            </div>
        `;
    });

    document.getElementById("subtotal").innerText = subtotal.toFixed(2);
    document.getElementById("gst").innerText = gstTotal.toFixed(2);
    document.getElementById("grand-total").innerText =
        (subtotal + gstTotal).toFixed(2);
}

function checkout() {
    if (cart.length === 0) {
        showToast("Cart is empty", "error");
        return;
    }

    fetch("/api/billing/checkout", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            cart_items: cart
        })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(err => {
                throw new Error(err.message);
            });
        }
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);

        // open PDF
        window.open(url, "_blank");

        showToast("Bill generated!", "success");

        cart = [];
        renderCart();
    })
    .catch(err => {
        console.error(err);
        showToast(err.message || "Something went wrong", "error");
    });
}
function showToast(message, type="success") {
    const toast = document.getElementById("toast");

    toast.innerText = message;
    toast.className = "toast show " + type;

    setTimeout(() => {
        toast.className = "toast";
    }, 2500);
}