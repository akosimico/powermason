console.log("logged 2");
document.addEventListener("DOMContentLoaded", () => {
    // ---------- Modal ----------
    const modal = document.getElementById("addUserModal");
    const openModalBtn = document.getElementById("openModalBtn");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const userSearchInput = document.getElementById("userSearchInput");
    const userSearchResults = document.getElementById("userSearchResults");
    const selectedUserId = document.getElementById("selectedUserId");
    const addUserForm = document.getElementById("addUserForm");

    openModalBtn.addEventListener("click", () => modal.classList.remove("hidden"));
    closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));

    // ---------- Modal Live Search ----------
    let searchTimeout = null;
    userSearchInput.addEventListener("input", () => {
        const query = userSearchInput.value.trim();
        if (searchTimeout) clearTimeout(searchTimeout);

        if (!query) {
            userSearchResults.innerHTML = "";
            userSearchResults.classList.add("hidden");
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/search-users/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    userSearchResults.innerHTML = "";
                    if (data.length === 0) {
                        userSearchResults.classList.add("hidden");
                        return;
                    }

                    data.forEach(user => {
                        const li = document.createElement("li");
                        li.classList.add("flex", "justify-between", "items-center", "px-4", "py-2", "hover:bg-blue-100", "cursor-pointer", "border-b");

                        li.innerHTML = `
                            <div class="flex flex-col flex-1">
                                <div class="flex gap-2">
                                    <span class="truncate font-medium">${user.username}</span>
                                    <span class="truncate">${user.full_name || '-'}</span>
                                </div>
                                <div class="text-gray-500 text-sm truncate mt-1">${user.email || '-'}</div>
                            </div>
                            <div class="ml-4 font-semibold text-gray-700 whitespace-nowrap">${user.role || '-'}</div>
                        `;

                        li.dataset.userId = user.id;

                        li.addEventListener("click", () => {
                            selectedUserId.value = user.id;
                            userSearchInput.value = `${user.full_name || user.username} (${user.email || ''})`;
                            userSearchResults.innerHTML = "";
                            userSearchResults.classList.add("hidden");
                        });

                        userSearchResults.appendChild(li);
                    });

                    userSearchResults.classList.remove("hidden");
                });
        }, 300);
    });

    // Hide dropdown if clicked outside
    document.addEventListener("click", (e) => {
        if (!userSearchInput.contains(e.target) && !userSearchResults.contains(e.target)) {
            userSearchResults.classList.add("hidden");
        }
    });

    addUserForm.addEventListener("submit", (e) => {
        if (!selectedUserId.value) {
            e.preventDefault();
            alert("Please select a user from the search results.");
        }
    });

    // ---------- Table Live Search & Filter ----------
    const tableSearchInput = document.getElementById("tableSearchInput");
    const roleFilter = document.getElementById("roleFilter");
    const tableBody = document.getElementById("tableBody");
    const allRows = Array.from(tableBody.querySelectorAll("tr")).filter(row => row.querySelector("form"));

    const filterTable = () => {
        const query = tableSearchInput.value.toLowerCase();
        const role = roleFilter.value;
        let visibleCount = 0;

        allRows.forEach(row => {
            const username = row.cells[0].innerText.toLowerCase();
            const fullName = row.cells[1].querySelector('input').value.toLowerCase();
            const userRole = row.cells[2].dataset.role;

            const matchesQuery = username.includes(query) || fullName.includes(query);
            const matchesRole = !role || userRole === role;

            if (matchesQuery && matchesRole) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });

        let noRow = document.getElementById("noProfilesRow");
        if (!noRow) {
            noRow = document.createElement("tr");
            noRow.id = "noProfilesRow";
            noRow.innerHTML = `<td colspan="4" class="text-center p-4 text-gray-500">No profiles found.</td>`;
            tableBody.appendChild(noRow);
        }
        noRow.style.display = visibleCount === 0 ? "" : "none";
    };

    const sortRowsByUpdated = () => {
        const rowsArray = Array.from(tableBody.querySelectorAll("tr")).filter(row => row.querySelector("form"));
        rowsArray.sort((a, b) => parseInt(b.dataset.updated) - parseInt(a.dataset.updated));
        rowsArray.forEach(row => tableBody.appendChild(row));
    };

    const updateTable = () => {
        filterTable();
        sortRowsByUpdated();
    };

    tableSearchInput.addEventListener("input", updateTable);
    roleFilter.addEventListener("change", updateTable);

    allRows.forEach(row => {
        const form = row.querySelector("form");
        if (!form) return;
        form.addEventListener("submit", (e) => {
            const roleSelect = row.querySelector('select[name="role"]');
            const profileIdInput = row.querySelector('input[name="profile_id"]');

            if (!profileIdInput.value || !roleSelect.value) {
                e.preventDefault();
                alert("Please select a user and role");
                return;
            }
            tableBody.insertBefore(row, tableBody.firstChild);
        });
    });

    updateTable();
});