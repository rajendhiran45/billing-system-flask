function openForm(){
    document.getElementById("productModal").style.display = "flex";
}

function closeForm(){
    document.getElementById("productModal").style.display = "none";
}

let deleteId = null;

function openDeleteModal(id) {
    deleteId = id;
    document.getElementById("deleteModal").style.display = "flex";
}

function closeDeleteModal() {
    deleteId = null;
    document.getElementById("deleteModal").style.display = "none";
}

function confirmDelete() {
    if (!deleteId) return;

    fetch(`/api/products/delete/${deleteId}`, {
        method: "DELETE"
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            closeDeleteModal();
            location.reload();
        } else {
            alert("Delete failed");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Something went wrong");
    });
}

function openEditModal(id, name, price, stock, gst) {
    document.getElementById("edit-id").value = id;
    document.getElementById("edit-name").value = name;
    document.getElementById("edit-price").value = price;
    document.getElementById("edit-stock").value = stock;
    document.getElementById("edit-gst").value = gst;

    document.getElementById("editModal").style.display = "flex";
}

function closeEditModal() {
    document.getElementById("editModal").style.display = "none";
}

document.getElementById("editForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const id = document.getElementById("edit-id").value;

    let formData = new FormData();
    formData.append("name", document.getElementById("edit-name").value);
    formData.append("price", document.getElementById("edit-price").value);
    formData.append("stock", document.getElementById("edit-stock").value);
    formData.append("gst_percent", document.getElementById("edit-gst").value);

    const image = document.getElementById("edit-image").files[0];
    if (image) {
        formData.append("image", image);
    }

    fetch(`/api/products/edit/${id}`, {
        method: "PUT",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            closeEditModal();
            location.reload();
        } else {
            alert("Update failed");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Something went wrong");
    });
});

// Client-side product search and stock filters. These only filter the displayed
// catalogue; all prices and stock checks remain server-side.
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("productSearch");
    const stockFilter = document.getElementById("stockFilter");
    const clearButton = document.getElementById("clearProductFilters");
    const countLabel = document.getElementById("catalogueCount");
    const resultsLabel = document.getElementById("filterResults");
    const cards = Array.from(document.querySelectorAll("#productsGrid .product-card"));

    if (!searchInput || !stockFilter) return;

    function applyProductFilters() {
        const query = searchInput.value.trim().toLocaleLowerCase();
        const filter = stockFilter.value;
        let visible = 0;

        cards.forEach(card => {
            const name = card.dataset.productName || "";
            const stock = Number(card.dataset.stock || 0);
            const threshold = Number(card.dataset.lowStockThreshold || 5);
            const matchesName = name.includes(query);
            const matchesStock = filter === "all"
                || (filter === "available" && stock > 0)
                || (filter === "low" && stock > 0 && stock <= threshold)
                || (filter === "out" && stock <= 0);
            const show = matchesName && matchesStock;
            card.hidden = !show;
            if (show) visible += 1;
        });

        if (countLabel) countLabel.textContent = `${visible} of ${cards.length} products`;
        if (resultsLabel) resultsLabel.textContent = `Showing ${visible} product${visible === 1 ? "" : "s"}`;
    }

    searchInput.addEventListener("input", applyProductFilters);
    stockFilter.addEventListener("change", applyProductFilters);
    if (clearButton) {
        clearButton.addEventListener("click", function () {
            searchInput.value = "";
            stockFilter.value = "all";
            applyProductFilters();
            searchInput.focus();
        });
    }
    applyProductFilters();
});

function setStockFilter(value) {
    const filter = document.getElementById("stockFilter");
    if (!filter) return;
    filter.value = value;
    filter.dispatchEvent(new Event("change"));
    document.getElementById("productSearch")?.focus();
}
