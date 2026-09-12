/**
 * MOVIEFLIX - CLIENT INTERACTION SCRIPTS
 */

// Global state for autocomplete caching
let cachedTitles = null;

/**
 * Autocomplete Movie Search Suggestions
 */
async function getSuggestions() {
    const inputElement = document.getElementById("movieInput");
    const suggestionsDiv = document.getElementById("suggestions");

    if (!inputElement || !suggestionsDiv) return;

    const query = inputElement.value.trim().toLowerCase();

    if (!query) {
        suggestionsDiv.innerHTML = "";
        return;
    }

    try {
        if (!cachedTitles) {
            const response = await fetch("/titles");
            cachedTitles = await response.json();
        }

        const matches = cachedTitles.filter(title => 
            title.toLowerCase().includes(query)
        );

        suggestionsDiv.innerHTML = "";

        if (matches.length === 0) {
            suggestionsDiv.innerHTML = `<div style="color: var(--text-muted); cursor: default;">No matching titles found</div>`;
            return;
        }

        matches.slice(0, 6).forEach(movie => {
            const safeMovie = movie.replace(/'/g, "\\'");
            suggestionsDiv.innerHTML += `
                <div onclick="selectMovie('${safeMovie}')">
                    <i class="fa-solid fa-film" style="color: var(--accent-purple);"></i>
                    <span>${movie}</span>
                </div>
            `;
        });
    } catch (err) {
        console.error("Error fetching title suggestions:", err);
    }
}

/**
 * Select title from autocomplete suggestion
 */
function selectMovie(movieTitle) {
    const inputElement = document.getElementById("movieInput");
    const suggestionsDiv = document.getElementById("suggestions");
    if (inputElement) inputElement.value = movieTitle;
    if (suggestionsDiv) suggestionsDiv.innerHTML = "";
}

// Close autocomplete when clicking outside
document.addEventListener("click", function (event) {
    const suggestionsDiv = document.getElementById("suggestions");
    const inputElement = document.getElementById("movieInput");
    if (suggestionsDiv && !event.target.closest("#suggestions") && event.target !== inputElement) {
        suggestionsDiv.innerHTML = "";
    }
});

/**
 * Intersection Observer for Lazy Hydrating Poster Artwork
 */
function initPosterLazyLoading() {
    const cards = document.querySelectorAll(".lazy-poster-card");
    if (!cards.length) return;

    const posterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;

            const card = entry.target;
            const title = card.dataset.movieTitle;
            const posterWrapper = card.querySelector(".poster-box");

            if (!title || !posterWrapper) return;

            fetch(`/movie-details?title=${encodeURIComponent(title)}`)
                .then(res => res.json())
                .then(details => {
                    if (details && details.poster && details.poster !== "N/A") {
                        posterWrapper.innerHTML = `
                            <img class="poster-img" src="${details.poster}" alt="${title}" loading="lazy">
                            <div class="card-overlay">
                                ${card.querySelector(".card-overlay") ? card.querySelector(".card-overlay").innerHTML : ''}
                            </div>
                        `;
                    }
                })
                .catch(err => console.warn("Failed to load poster for:", title, err))
                .finally(() => observer.unobserve(card));
        });
    }, { rootMargin: "300px" });

    cards.forEach(card => posterObserver.observe(card));
}

/**
 * Movie Details Modal Controller
 */
async function openMovieDetailsModal(movieTitle) {
    let backdrop = document.getElementById("movieDetailsModal");
    
    if (!backdrop) {
        // Create backdrop dynamically if not in DOM
        backdrop = document.createElement("div");
        backdrop.id = "movieDetailsModal";
        backdrop.className = "modal-backdrop";
        document.body.appendChild(backdrop);
    }

    // Show loading skeleton in modal
    backdrop.innerHTML = `
        <div class="modal-card">
            <button class="modal-close-btn" onclick="closeMovieDetailsModal()">&times;</button>
            <div class="modal-poster-col" style="display:flex; align-items:center; justify-content:center;">
                <i class="fa-solid fa-spinner fa-spin" style="font-size:2rem; color:var(--accent-purple);"></i>
            </div>
            <div class="modal-info-col">
                <h2 class="modal-title">Loading ${movieTitle}...</h2>
            </div>
        </div>
    `;
    backdrop.classList.add("active");

    try {
        const response = await fetch(`/movie-details?title=${encodeURIComponent(movieTitle)}`);
        const details = await response.json();

        const posterSrc = details.poster && details.poster !== "N/A" 
            ? details.poster 
            : null;
        
        const ratingStr = details.rating && details.rating !== "N/A" ? details.rating : "N/A";
        const genreStr = details.genre && details.genre !== "N/A" ? details.genre : "N/A";
        const yearStr = details.year && details.year !== "N/A" ? details.year : "N/A";
        const plotStr = details.plot || `Discover and enjoy "${movieTitle}". Add it to your favorites or watch later list to receive personalized recommendations on MovieFlix!`;

        const youtubeQuery = encodeURIComponent(`${movieTitle} official trailer`);
        const youtubeUrl = `https://www.youtube.com/results?search_query=${youtubeQuery}`;

        backdrop.innerHTML = `
            <div class="modal-card">
                <button class="modal-close-btn" onclick="closeMovieDetailsModal()">&times;</button>

                <div class="modal-poster-col">
                    ${posterSrc 
                        ? `<img src="${posterSrc}" alt="${movieTitle}">`
                        : `<div class="poster-placeholder"><i class="fa-solid fa-clapperboard"></i><p>${movieTitle}</p></div>`
                    }
                </div>

                <div class="modal-info-col">
                    <h2 class="modal-title">${movieTitle}</h2>

                    <div class="modal-meta-pills">
                        <span class="pill-item gold"><i class="fa-solid fa-star"></i> IMDb ${ratingStr}</span>
                        <span class="pill-item"><i class="fa-solid fa-masks-theater"></i> ${genreStr}</span>
                        <span class="pill-item"><i class="fa-solid fa-calendar"></i> ${yearStr}</span>
                    </div>

                    <p class="modal-plot">${plotStr}</p>

                    <div class="modal-actions">
                        <a href="${youtubeUrl}" target="_blank" rel="noopener" class="btn-trailer">
                            <i class="fa-solid fa-play"></i> Watch Trailer
                        </a>

                        <form action="/favorite" method="POST" style="display:inline;">
                            <input type="hidden" name="movie" value="${movieTitle}">
                            <button type="submit" class="btn-action-icon fav" style="padding: 12px 20px;">
                                <i class="fa-solid fa-heart"></i> Favorite
                            </button>
                        </form>

                        <form action="/watch-later" method="POST" style="display:inline;">
                            <input type="hidden" name="movie" value="${movieTitle}">
                            <button type="submit" class="btn-action-icon watch" style="padding: 12px 20px;">
                                <i class="fa-solid fa-bookmark"></i> Watch Later
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        console.error("Failed to load details for modal:", err);
    }
}

function closeMovieDetailsModal() {
    const backdrop = document.getElementById("movieDetailsModal");
    if (backdrop) {
        backdrop.classList.remove("active");
    }
}

// Close modal on Escape key
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMovieDetailsModal();
});

// Initialize observers on DOM load
document.addEventListener("DOMContentLoaded", function () {
    initPosterLazyLoading();
});
