
/* ==========================================
   Billing System - Billing Page JavaScript
   Checkout sends product IDs and quantities
   Only. Prices and GST are validated by Flask.
========================================== */

"use strict";

let cart = [];
let checkoutInProgress = false;
let toastTimeout = null;

/* ------------------------------------------
   Helpers
------------------------------------------ */

function formatCurrency(value) {
    return Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function getElement(id) {
    return document.getElementById(id);
}

function displayedMoney(id) {
    return Number(
        (getElement(id)?.textContent || "0").replace(/,/g, "")
    ) || 0;
}

function roundMoney(value) {
    return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
}

function automaticDiscountRate(subtotal) {
    if (subtotal >= 5000) return 15;
    if (subtotal >= 2000) return 10;
    if (subtotal >= 1000) return 5;
    return 0;
}

function currentFinalTotal() {
    const subtotal = displayedMoney("subtotal");
    const gst = displayedMoney("gst");
    const discount = roundMoney(subtotal * automaticDiscountRate(subtotal) / 100);
    const points = Math.max(0, Math.floor(Number(getElement("loyalty-points")?.value || 0)));
    const redemption = Math.min(roundMoney(points * 0.10), roundMoney(Math.max(0, subtotal - discount) * 0.20));
    const netSubtotal = roundMoney(Math.max(0, subtotal - discount - redemption));
    const adjustedGst = subtotal > 0 ? gst * (netSubtotal / subtotal) : 0;
    return Math.max(0, roundMoney(netSubtotal + adjustedGst));
}

function selectedPaymentChoice() {
    return document.querySelector('input[name="payment-choice"]:checked')?.value || "cash";
}

function addPaymentSplit() {
    const section = getElement("payment-split-rows");
    if (!section) return;
    const row = document.createElement("div");
    row.className = "payment-row";
    row.innerHTML = '<select class="payment-method"><option value="cash">Cash</option><option value="upi">UPI</option><option value="card">Card</option></select><input class="payment-amount" type="number" min="0.01" step="0.01" placeholder="Amount"><button type="button" class="remove-item-btn">Remove</button>';
    row.querySelector("button").addEventListener("click", () => row.remove());
    section.insertBefore(row, getElement("add-payment-split"));
}


function collectPayments() {
    const total = currentFinalTotal();
    const choice = selectedPaymentChoice();

    if (!Number.isFinite(total) || total <= 0) {
        throw new Error(
            "The bill total must be greater than zero."
        );
    }

    // Cash, UPI, or card: automatically use the final total.
    if (choice !== "split") {
        if (!["cash", "upi", "card"].includes(choice)) {
            throw new Error("Choose a valid payment method.");
        }

        return [{
            method: choice,
            amount: Math.round(total * 100) / 100,
        }];
    }

    // Split payment: validate each entered amount.
    const rows = Array.from(
        document.querySelectorAll(
            "#payment-split-rows .payment-row"
        )
    );

    if (rows.length < 2) {
        throw new Error(
            "Add at least two payment entries for split payment."
        );
    }

    const payments = rows.map((row) => ({
        method: row.querySelector(".payment-method")?.value,
        amount: Number(
            row.querySelector(".payment-amount")?.value
        ),
    }));

    const valid = payments.every((payment) =>
        ["cash", "upi", "card"].includes(payment.method) &&
        Number.isFinite(payment.amount) &&
        payment.amount > 0
    );

    if (!valid) {
        throw new Error(
            "Each payment amount must be valid."
        );
    }

    const enteredCents = payments.reduce(
        (sum, payment) =>
            sum + Math.round(payment.amount * 100),
        0
    );

    const expectedCents = Math.round(total * 100);

    if (enteredCents !== expectedCents) {
        throw new Error(
            "Split payment amounts must equal the final bill total."
        );
    }

    return payments;
}


function updateLoyaltyBalance() {
    const select = getElement("customer-id");
    const option = select?.selectedOptions?.[0];
    const points = Number(option?.dataset?.points || 0);
    const lifetime = Number(option?.dataset?.lifetimePoints || 0);
    const label = getElement("loyalty-balance");
    if (label) label.textContent = select?.value
        ? `Available: ${points} points · Lifetime earned: ${lifetime} points · 100 points = ₹10.`
        : "Walk-in customers do not earn or redeem points. 100 points = ₹10.";
    const input = getElement("loyalty-points");
    if (input) {
        input.max = String(points);
        if (!select?.value) input.value = "0";
    }
}

/* ------------------------------------------
   Add a product to the cart
------------------------------------------ */

function addToCart(card) {
    if (checkoutInProgress) return;

    const productId = Number(card.dataset.id);
    const name = card.dataset.name || "Product";
    const price = Number(card.dataset.price);
    const gstPercent = Number(card.dataset.gst);
    const stock = Number(card.dataset.stock);

    if (
        !Number.isInteger(productId) ||
        !Number.isFinite(price) ||
        !Number.isFinite(gstPercent) ||
        !Number.isInteger(stock) ||
        stock < 1
    ) {
        showToast("This product is unavailable.", "error");
        return;
    }

    const existingItem = cart.find(
        item => item.product_id === productId
    );

    if (existingItem) {
        if (existingItem.quantity >= stock) {
            showToast("You cannot add more than the available stock.", "error");
            return;
        }

        existingItem.quantity += 1;
    } else {
        cart.push({
            product_id: productId,
            product_name: name,

            // These values are for the on-screen estimate only.
            // They are NOT sent to the server during checkout.
            display_price: price,
            display_gst_percent: gstPercent,

            stock: stock,
            quantity: 1
        });
    }

    renderCart();
    showToast(name + " added to cart.", "success");
}

/* ------------------------------------------
   Change product quantity
------------------------------------------ */

function changeQuantity(productId, change) {
    if (checkoutInProgress) return;

    const item = cart.find(
        product => product.product_id === Number(productId)
    );

    if (!item) return;

    const newQuantity = item.quantity + change;

    if (newQuantity < 1) {
        removeFromCart(productId);
        return;
    }

    if (newQuantity > item.stock) {
        showToast("Available stock: " + item.stock, "error");
        return;
    }

    item.quantity = newQuantity;
    renderCart();
}

/* ------------------------------------------
   Remove a product
------------------------------------------ */

function removeFromCart(productId) {
    if (checkoutInProgress) return;

    cart = cart.filter(
        item => item.product_id !== Number(productId)
    );

    renderCart();
}

/* ------------------------------------------
   Clear the entire cart
------------------------------------------ */

function clearCart() {
    if (checkoutInProgress || cart.length === 0) return;

    cart = [];
    renderCart();
    showToast("Cart cleared.", "success");
}

/* ------------------------------------------
   Render cart and totals
------------------------------------------ */

function renderCart() {
    const cartBox = getElement("cart-items");

    if (!cartBox) return;

    cartBox.replaceChildren();

    let subtotal = 0;
    let gstTotal = 0;
    let totalQuantity = 0;

    const emptyCart = document.createElement("div");
    emptyCart.className = "empty-cart";
    emptyCart.id = "empty-cart";

    const emptyIcon = document.createElement("div");
    emptyIcon.className = "empty-cart-icon";
    emptyIcon.textContent = "+";

    const emptyTitle = document.createElement("h4");
    emptyTitle.textContent = "Your cart is empty";

    const emptyMessage = document.createElement("p");
    emptyMessage.textContent =
        "Select a product to begin your transaction.";

    emptyCart.append(emptyIcon, emptyTitle, emptyMessage);

    cart.forEach(item => {
        const lineSubtotal = item.display_price * item.quantity;
        const lineGst =
            lineSubtotal * item.display_gst_percent / 100;

        subtotal += lineSubtotal;
        gstTotal += lineGst;
        totalQuantity += item.quantity;

        const row = document.createElement("div");
        row.className = "cart-item";

        const details = document.createElement("div");
        details.className = "cart-item-details";

        const name = document.createElement("p");
        name.className = "cart-item-name";
        name.textContent = item.product_name;

        const price = document.createElement("div");
        price.className = "cart-item-price";
        price.textContent =
            "₹" + formatCurrency(item.display_price) + " each";

        const controls = document.createElement("div");
        controls.className = "cart-item-controls";

        const minusButton = document.createElement("button");
        minusButton.type = "button";
        minusButton.className = "quantity-btn";
        minusButton.textContent = "−";
        minusButton.setAttribute(
            "aria-label",
            "Decrease quantity of " + item.product_name
        );
        minusButton.disabled = checkoutInProgress;
        minusButton.addEventListener("click", () => {
            changeQuantity(item.product_id, -1);
        });

        const quantity = document.createElement("span");
        quantity.className = "quantity-value";
        quantity.textContent = String(item.quantity);

        const plusButton = document.createElement("button");
        plusButton.type = "button";
        plusButton.className = "quantity-btn";
        plusButton.textContent = "+";
        plusButton.setAttribute(
            "aria-label",
            "Increase quantity of " + item.product_name
        );
        plusButton.disabled =
            checkoutInProgress || item.quantity >= item.stock;
        plusButton.addEventListener("click", () => {
            changeQuantity(item.product_id, 1);
        });

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "remove-item-btn";
        removeButton.textContent = "Remove";
        removeButton.disabled = checkoutInProgress;
        removeButton.addEventListener("click", () => {
            removeFromCart(item.product_id);
        });

        controls.append(
            minusButton,
            quantity,
            plusButton,
            removeButton
        );

        details.append(name, price, controls);

        const lineTotal = document.createElement("div");
        lineTotal.className = "cart-line-total";
        lineTotal.textContent = "₹" + formatCurrency(lineSubtotal);

        row.append(details, lineTotal);
        cartBox.appendChild(row);
    });

    if (cart.length === 0) {
        cartBox.appendChild(emptyCart);
    }

    if (getElement("subtotal")) {
        getElement("subtotal").textContent = formatCurrency(subtotal);
    }

    if (getElement("gst")) {
        getElement("gst").textContent = formatCurrency(gstTotal);
    }

    if (getElement("grand-total")) {
        const discount = roundMoney(subtotal * automaticDiscountRate(subtotal) / 100);
        const points = Math.max(0, Math.floor(Number(getElement("loyalty-points")?.value || 0)));
        const redemption = Math.min(roundMoney(points * 0.10), roundMoney(Math.max(0, subtotal - discount) * 0.20));
        const netSubtotal = roundMoney(Math.max(0, subtotal - discount - redemption));
        const adjustedGst = subtotal > 0 ? gstTotal * (netSubtotal / subtotal) : 0;
        getElement("grand-total").textContent = formatCurrency(netSubtotal + adjustedGst);
    }

    if (getElement("cart-count")) {
        getElement("cart-count").textContent =
            totalQuantity + (totalQuantity === 1 ? " item" : " items");
    }

    const checkoutButton = getElement("checkout-btn");
    const clearButton = getElement("clear-cart-btn");

    if (checkoutButton) {
        checkoutButton.disabled =
            cart.length === 0 || checkoutInProgress;

        checkoutButton.querySelector("span").textContent =
            checkoutInProgress ? "Generating bill..." : "Generate Bill";
    }

    if (clearButton) {
        clearButton.disabled =
            cart.length === 0 || checkoutInProgress;
    }
}

/* ------------------------------------------
   Refresh product stock from Flask
------------------------------------------ */

async function refreshProductStock() {
    try {
        const response = await fetch("/api/billing/products", {
            method: "GET",
            headers: {
                "Accept": "application/json"
            },
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Could not fetch current product stock.");
        }

        const data = await response.json();

        if (data.status !== "success" || !Array.isArray(data.products)) {
            throw new Error("Invalid stock response from server.");
        }

        data.products.forEach(product => {
            const card = document.querySelector(
                `.billing-products .product-card[data-id="${product.id}"]`
            );

            if (!card) return;

            const stock = Math.max(0, Number(product.stock) || 0);

            // Update the stock value used by addToCart().
            card.dataset.stock = String(stock);

            // Update the visible stock count.
            const stockInfo = card.querySelector(".stock-info");
            if (stockInfo) {
                stockInfo.textContent = `${stock} available`;
            }

            // Update the stock badge.
            let badge = card.querySelector(".stock-badge");

            if (badge) {
                badge.classList.toggle("out-of-stock", stock === 0);
                badge.classList.toggle("in-stock", stock > 0);
                badge.textContent = stock === 0
                    ? "Out of stock"
                    : "In stock";
            }

            // Update the product card's availability.
            card.classList.toggle("disabled", stock === 0);

            if (stock === 0) {
                card.removeAttribute("onclick");
                card.removeAttribute("onkeydown");
                card.removeAttribute("role");
                card.removeAttribute("tabindex");
            } else {
                card.setAttribute("onclick", "addToCart(this)");
                card.setAttribute("onkeydown",
                    "if(event.key === 'Enter' || event.key === ' '){event.preventDefault();addToCart(this)}"
                );
                card.setAttribute("role", "button");
                card.setAttribute("tabindex", "0");
            }

            // Update the plus icon / unavailable label.
            const addIcon = card.querySelector(".add-product-icon");
            const unavailableLabel = card.querySelector(".unavailable-label");

            if (stock === 0) {
                if (addIcon) addIcon.remove();

                if (!unavailableLabel) {
                    const label = document.createElement("span");
                    label.className = "unavailable-label";
                    label.textContent = "Unavailable";

                    const bottom = card.querySelector(".product-bottom");
                    if (bottom) bottom.appendChild(label);
                }
            } else {
                if (unavailableLabel) unavailableLabel.remove();

                if (!addIcon) {
                    const icon = document.createElement("span");
                    icon.className = "add-product-icon";
                    icon.setAttribute("aria-hidden", "true");
                    icon.textContent = "+";

                    const bottom = card.querySelector(".product-bottom");
                    if (bottom) bottom.appendChild(icon);
                }
            }
        });

        // Keep cart quantities within the newly available stock.
        cart = cart.filter(item => {
            const product = data.products.find(
                p => Number(p.id) === item.product_id
            );

            if (!product) return true;

            const latestStock = Math.max(0, Number(product.stock) || 0);

            if (latestStock === 0) {
                showToast(`${item.product_name} is now out of stock.`, "error");
                return false;
            }

            item.stock = latestStock;

            if (item.quantity > latestStock) {
                item.quantity = latestStock;
                showToast(
                    `${item.product_name} quantity adjusted to available stock.`,
                    "error"
                );
            }

            return true;
        });

        renderCart();

    } catch (error) {
        console.error("Stock refresh error:", error);
    }
}


function initializeCustomerSearch() {
    const searchInput = document.getElementById("customer-search");
    const customerSelect = document.getElementById("customer-id");
    const status = document.getElementById("customer-search-status");

    if (!searchInput || !customerSelect) return;

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        Array.from(customerSelect.options).forEach((option, index) => {
            if (index === 0) {
                option.hidden = false;
                return;
            }

            const name = option.dataset.name || option.textContent.toLowerCase();
            const phone = option.dataset.phone || "";

            const matches = name.includes(query) || phone.includes(query);
            option.hidden = !matches;

            if (matches) visibleCount++;
        });

        if (status) {
            status.textContent = query
                ? `${visibleCount} matching customer(s). Select a matching customer below.`
                : "Choose a customer or leave Walk-in customer selected.";
        }

        // Clear a selected customer if it no longer matches the search.
        const selectedOption = customerSelect.selectedOptions[0];

        if (
            selectedOption &&
            selectedOption.value !== "" &&
            selectedOption.hidden
        ) {
            customerSelect.value = "";
        }
    });

    customerSelect.addEventListener("change", () => {
        if (status) {
            status.textContent = customerSelect.value
                ? `Selected: ${customerSelect.selectedOptions[0].textContent.trim()}`
                : "Walk-in customer selected.";
        }
    });
}


async function createQuickCustomer() {
    const saveButton = getElement("quick-customer-save");
    const name = getElement("quick-customer-name")?.value.trim() || "";
    const phone = getElement("quick-customer-phone")?.value.trim() || "";
    const email = getElement("quick-customer-email")?.value.trim() || "";
    const address = getElement("quick-customer-address")?.value.trim() || "";

    if (!name) {
        showToast("Enter the customer's name.", "error");
        getElement("quick-customer-name")?.focus();
        return;
    }

    if (saveButton) saveButton.disabled = true;

    try {
        const response = await fetch("/api/customers/quick-create", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ name, phone, email, address })
        });
        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            throw new Error(data.message || "Could not save customer.");
        }

        const customer = data.customer;
        const select = getElement("customer-id");
        const search = getElement("customer-search");
        const option = document.createElement("option");
        option.value = String(customer.id);
        option.dataset.name = customer.name.toLowerCase();
        option.dataset.phone = (customer.phone || "").toLowerCase();
        option.dataset.points = "0";
        option.dataset.lifetimePoints = "0";
        option.textContent = customer.name + (customer.phone ? ` · ${customer.phone}` : "");
        select?.appendChild(option);

        if (select) select.value = option.value;
        if (search) search.value = option.textContent;
        ["quick-customer-name", "quick-customer-phone", "quick-customer-email", "quick-customer-address"].forEach(id => {
            const input = getElement(id);
            if (input) input.value = "";
        });
        const panel = getElement("quick-customer-panel");
        if (panel) panel.open = false;
        updateLoyaltyBalance();
        renderCart();
        showToast("Customer saved and selected.", "success");
    } catch (error) {
        showToast(error.message || "Could not save customer.", "error");
    } finally {
        if (saveButton) saveButton.disabled = false;
    }
}

/* ------------------------------------------
   Checkout
------------------------------------------ */

async function checkout() {
    if (checkoutInProgress) return;

    if (cart.length === 0) {
        showToast("Your cart is empty.", "error");
        return;
    }

    /*
       Critical security rule:
       Only send product_id and quantity.
       Do not send browser-calculated prices,
       GST percentages, or totals.
    */

    const cartItems = cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
    }));
    const customerValue = getElement("customer-id")?.value;

    checkoutInProgress = true;
    renderCart();

    try {
        const response = await fetch("/api/billing/checkout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/pdf, application/json"
            },
            body: JSON.stringify({
                cart_items: cartItems,
                customer_id: customerValue ? Number(customerValue) : null,
                loyalty_points_redeemed: Number(getElement("loyalty-points")?.value || 0),
                payments: collectPayments()
            })
        });

        if (!response.ok) {
            let message = "Unable to generate the bill.";

            try {
                const errorData = await response.json();
                if (errorData.message) {
                    message = errorData.message;
                }
            } catch {
                // The server may return a non-JSON error response.
            }

            throw new Error(message);
        }

        const blob = await response.blob();

        if (
            blob.type &&
            !blob.type.includes("application/pdf")
        ) {
            throw new Error(
                "The server response was not a PDF. Please check the Flask logs."
            );
        }

        const pdfUrl = URL.createObjectURL(blob);
        const pdfWindow = window.open(pdfUrl, "_blank");

        if (!pdfWindow) {
            const link = document.createElement("a");
            link.href = pdfUrl;
            link.download = "bill.pdf";
            document.body.appendChild(link);
            link.click();
            link.remove();
        }

        cart = [];
        await refreshProductStock();
        showToast("Bill generated successfully.", "success");

        // Keep the PDF URL alive briefly for the new tab to load.
        setTimeout(() => URL.revokeObjectURL(pdfUrl), 60000);

    } catch (error) {
        console.error("Checkout error:", error);

        showToast(
            error.message || "Something went wrong during checkout.",
            "error"
        );
    } finally {
        checkoutInProgress = false;
        renderCart();
    }
}

function initializeCustomerSearch() {
    const searchInput = document.getElementById("customer-search");
    const customerSelect = document.getElementById("customer-id");
    const status = document.getElementById("customer-search-status");

    if (!searchInput || !customerSelect) return;

    const customers = Array.from(customerSelect.options)
        .filter(option => option.value !== "")
        .map(option => ({
            id: option.value,
            name: option.dataset.name || option.textContent.toLowerCase(),
            phone: option.dataset.phone || "",
            label: option.textContent.trim()
        }));

    let resultsContainer = document.getElementById("customer-search-results");

    if (!resultsContainer) {
        resultsContainer = document.createElement("div");
        resultsContainer.id = "customer-search-results";
        resultsContainer.style.cssText =
            "display:none; max-height:180px; overflow-y:auto; " +
            "border:1px solid #ccc; border-radius:6px; " +
            "background:white; color:#222; margin-top:4px;";

        searchInput.insertAdjacentElement("afterend", resultsContainer);
    }

    function closeResults() {
        resultsContainer.style.display = "none";
    }

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        resultsContainer.replaceChildren();

        if (!query) {
            closeResults();
            if (status) status.textContent = "";
            return;
        }

        const matches = customers.filter(customer =>
            customer.name.includes(query) ||
            customer.phone.includes(query)
        );

        if (matches.length === 0) {
            closeResults();
            if (status) status.textContent = "No matching customers found.";
            return;
        }

        matches.forEach(customer => {
            const option = document.createElement("button");
            option.type = "button";
            option.textContent = customer.label;
            option.style.cssText =
                "display:block; width:100%; padding:9px; border:0; " +
                "text-align:left; background:white; color:#222; cursor:pointer;";

            option.addEventListener("click", () => {
                customerSelect.value = customer.id;
                searchInput.value = customer.label;
                closeResults();

                if (status) {
                    status.textContent = "Selected: " + customer.label;
                }
            });

            resultsContainer.appendChild(option);
        });

        resultsContainer.style.display = "block";
        if (status) status.textContent = `${matches.length} customer(s) found.`;
    });

    customerSelect.addEventListener("change", () => {
        if (!customerSelect.value) {
            searchInput.value = "";
            if (status) status.textContent = "";
        }
    });

    document.addEventListener("click", event => {
        if (
            event.target !== searchInput &&
            !resultsContainer.contains(event.target)
        ) {
            closeResults();
        }
    });
}

/* ------------------------------------------
   Toast notifications
------------------------------------------ */

function showToast(message, type = "success") {
    const toast = getElement("toast");

    if (!toast) {
        console.log(message);
        return;
    }

    if (toastTimeout) {
        clearTimeout(toastTimeout);
    }

    toast.textContent = message;
    toast.className = "toast show " + type;

    toastTimeout = setTimeout(() => {
        toast.className = "toast";
        toastTimeout = null;
    }, 2800);
}

function initializeBillingProductSearch() {
    const searchInput = document.getElementById("billing-product-search");
    const status = document.getElementById("billing-product-search-status");
    const grid = document.getElementById("billing-products-grid");

    if (!searchInput || !grid) return;

    const productCards = Array.from(grid.querySelectorAll(".product-card"));

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        productCards.forEach(card => {
            const name = (card.dataset.name || "").toLowerCase();
            const matches = name.includes(query);

            card.hidden = !matches;

            if (matches) visibleCount++;
        });

        if (status) {
            if (!query) {
                status.textContent = `${productCards.length} products available`;
            } else if (visibleCount === 0) {
                status.textContent = "No matching products found.";
            } else {
                status.textContent = `${visibleCount} product(s) found`;
            }
        }

        const emptyMessage = grid.querySelector(".billing-search-empty");

        if (emptyMessage) emptyMessage.remove();

        if (query && visibleCount === 0) {
            const message = document.createElement("p");
            message.className = "billing-search-empty";
            message.textContent = "No products match your search.";
            grid.appendChild(message);
        }
    });
}


/* ------------------------------------------
   Initialize page
------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
    renderCart();
    refreshProductStock();
    initializeCustomerSearch();
    initializeBillingProductSearch();
    getElement("loyalty-points")?.addEventListener("input", renderCart);
    getElement("customer-id")?.addEventListener("change", () => { updateLoyaltyBalance(); renderCart(); });
    document.querySelectorAll('input[name="payment-choice"]').forEach(input => input.addEventListener("change", () => {
        const split = selectedPaymentChoice() === "split";
        getElement("payment-split-rows").hidden = !split;
        getElement("payment-help").textContent = split
            ? "Enter each payment amount. Their sum must equal the final bill total."
            : `The full final amount will be assigned to ${selectedPaymentChoice().toUpperCase()}.`;
    }));
    getElement("add-payment-split")?.addEventListener("click", addPaymentSplit);
    getElement("quick-customer-save")?.addEventListener("click", createQuickCustomer);
    updateLoyaltyBalance();
});
