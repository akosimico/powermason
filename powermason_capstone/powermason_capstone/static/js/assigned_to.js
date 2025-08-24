document.addEventListener("DOMContentLoaded", () => {
    const containers = document.querySelectorAll(".assigned-to-container");

    containers.forEach(container => {
        const input = container.querySelector(".assigned-to-input");
        const hiddenField = container.querySelector(".assigned-to-hidden");
        const suggestionsBox = container.querySelector(".assigned-to-suggestions");

        async function fetchProjectManagers(query) {
            const response = await fetch(`/projects/search/project-managers/?q=${encodeURIComponent(query)}`);
            if (!response.ok) return [];
            return await response.json();
        }

        input.addEventListener("input", async () => {
            const query = input.value.trim();
            suggestionsBox.innerHTML = "";

            if (!query) {
                suggestionsBox.classList.add("hidden");
                return;
            }

            const results = await fetchProjectManagers(query);
            if (results.length === 0) {
                suggestionsBox.classList.add("hidden");
                return;
            }

            results.forEach(pm => {
                const li = document.createElement("li");
                li.className = "px-3 py-2 cursor-pointer hover:bg-gray-100";
                li.textContent = `${pm.username} / ${pm.full_name} / ${pm.email}`;
                li.addEventListener("click", () => {
                    input.value = pm.full_name;
                    hiddenField.value = pm.id;
                    suggestionsBox.classList.add("hidden");
                });
                suggestionsBox.appendChild(li);
            });

            suggestionsBox.classList.remove("hidden");
        });

        document.addEventListener("click", (e) => {
            if (!container.contains(e.target)) {
                suggestionsBox.classList.add("hidden");
            }
        });
    });
});
