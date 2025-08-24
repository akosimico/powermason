document.addEventListener("DOMContentLoaded", () => {
    const tableSearchInput = document.getElementById("tableSearchInput");
    const roleFilter = document.getElementById("roleFilter");
    const tableBody = document.getElementById("tableBody");

    // Grab all rows that contain a form
    const allRows = Array.from(tableBody.querySelectorAll("tr")).filter(row => row.querySelector("form"));

    const filterTable = () => {
        const query = tableSearchInput.value.toLowerCase().trim();
        const selectedRole = roleFilter.value;
        let visibleCount = 0;

        allRows.forEach(row => {
            const username = row.cells[0]?.innerText.toLowerCase() || '';
            const fullNameInput = row.querySelector('input[name="full_name"]');
            const fullName = fullNameInput ? fullNameInput.value.toLowerCase() : '';
            const email = row.cells[2]?.innerText.toLowerCase() || ''; // assuming column 2 is email
            const role = row.dataset.role || '';

            const matchesSearch = username.includes(query) || fullName.includes(query) || email.includes(query);
            const matchesRole = !selectedRole || role === selectedRole;

            row.style.display = (matchesSearch && matchesRole) ? "" : "none";
            if (matchesSearch && matchesRole) visibleCount++;
        });

        // Handle "No profiles found"
        let noRow = document.getElementById("noProfilesRow");
        if (!noRow) {
            noRow = document.createElement("tr");
            noRow.id = "noProfilesRow";
            noRow.innerHTML = `<td colspan="5" class="text-center p-4 text-gray-500">No profiles found.</td>`;
            tableBody.appendChild(noRow);
        }
        noRow.style.display = visibleCount === 0 ? "" : "none";
    };

    const sortRowsByUpdated = () => {
        const rowsArray = allRows.slice(); // clone array
        rowsArray.sort((a, b) => parseInt(b.dataset.updated) - parseInt(a.dataset.updated));
        rowsArray.forEach(row => tableBody.appendChild(row));
    };

    const updateTable = () => {
        filterTable();
        sortRowsByUpdated();
    };

    // Event listeners for search and role filter
    tableSearchInput.addEventListener("input", updateTable);
    roleFilter.addEventListener("change", updateTable);

    // Initial table update
    updateTable();
});
