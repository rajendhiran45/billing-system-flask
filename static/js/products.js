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