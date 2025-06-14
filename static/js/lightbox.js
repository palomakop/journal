// simple image lightbox with lazy loading
(function() {
    'use strict';
    
    let currentImages = [];
    let currentIndex = 0;
    let lightbox = null;
    let preloadedImages = new Set(); // track which images we've preloaded

    function createLightbox() {
        lightbox = document.createElement('div');
        lightbox.className = 'lightbox';
        lightbox.innerHTML = `
            <div class="lightbox-content">
                <button class="lightbox-close">&times;</button>
                <button class="lightbox-nav lightbox-prev">&lt;</button>
                <div class="lightbox-loading">loading...</div>
                <img class="lightbox-img" src="" alt="" style="display: none;">
                <button class="lightbox-nav lightbox-next">&gt;</button>
            </div>
        `;
        document.body.appendChild(lightbox);

        // event listeners
        lightbox.querySelector('.lightbox-close').onclick = closeLightbox;
        lightbox.querySelector('.lightbox-prev').onclick = () => navigate(-1);
        lightbox.querySelector('.lightbox-next').onclick = () => navigate(1);
        
        // close when clicking background (lightbox or lightbox-content, but not image or buttons)
        lightbox.onclick = (e) => { 
            if (e.target === lightbox || e.target.className === 'lightbox-content') {
                closeLightbox(); 
            }
        };
        
        document.addEventListener('keydown', handleKeydown);
    }

    function handleKeydown(e) {
        if (lightbox && lightbox.style.display === 'block') {
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') navigate(-1);
            if (e.key === 'ArrowRight') navigate(1);
        }
    }

    function preloadImage(url) {
        // don't preload if we already have
        if (preloadedImages.has(url)) return;
        
        const img = new Image();
        img.onload = () => preloadedImages.add(url);
        img.src = url;
    }

    function getNextIndex(direction) {
        let nextIndex = currentIndex + direction;
        if (nextIndex < 0) nextIndex = currentImages.length - 1;
        if (nextIndex >= currentImages.length) nextIndex = 0;
        return nextIndex;
    }

    function openLightbox(images, index) {
        if (!lightbox) createLightbox();
        currentImages = images;
        currentIndex = index;
        preloadedImages.clear(); // reset preload cache for new image set
        updateLightbox();
        lightbox.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        // preload next image when lightbox opens (if there are multiple images)
        if (currentImages.length > 1) {
            const nextIndex = getNextIndex(1);
            preloadImage(currentImages[nextIndex].fullUrl);
        }
    }

    function closeLightbox() {
        if (lightbox) {
            lightbox.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    function navigate(direction) {
        currentIndex += direction;
        if (currentIndex < 0) currentIndex = currentImages.length - 1;
        if (currentIndex >= currentImages.length) currentIndex = 0;
        updateLightbox();
        
        // preload the next image in the direction we're going
        if (currentImages.length > 1) {
            const nextIndex = getNextIndex(direction);
            preloadImage(currentImages[nextIndex].fullUrl);
        }
    }

    function updateLightbox() {
        if (!lightbox) return;
        
        const img = lightbox.querySelector('.lightbox-img');
        const loading = lightbox.querySelector('.lightbox-loading');
        const current = currentImages[currentIndex];
        
        // show loading, hide image
        loading.style.display = 'block';
        img.style.display = 'none';
        
        // create new image to preload
        const newImg = new Image();
        newImg.onload = function() {
            // image loaded successfully
            img.src = this.src;
            img.alt = current.alt;
            loading.style.display = 'none';
            img.style.display = 'block';
            preloadedImages.add(current.fullUrl); // mark as preloaded
        };
        newImg.onerror = function() {
            // image failed to load
            loading.textContent = 'failed to load image';
            setTimeout(() => {
                loading.style.display = 'none';
                loading.textContent = 'loading...'; // reset for next time
            }, 2000);
        };
        
        // start loading the image
        newImg.src = current.fullUrl;
        
        // hide nav buttons if only one image
        const prevBtn = lightbox.querySelector('.lightbox-prev');
        const nextBtn = lightbox.querySelector('.lightbox-next');
        if (currentImages.length <= 1) {
            prevBtn.style.display = 'none';
            nextBtn.style.display = 'none';
        } else {
            prevBtn.style.display = 'block';
            nextBtn.style.display = 'block';
        }
    }

    function initializeLightbox() {
        // find all articles (posts)
        document.querySelectorAll('article').forEach(article => {
            const imageLinks = article.querySelectorAll('.post-image a');
            if (imageLinks.length === 0) return;

            // collect image data for this post
            const images = Array.from(imageLinks).map(link => {
                const fullUrl = link.href; // use original href as full-size URL
                const img = link.querySelector('img');
                return {
                    fullUrl: fullUrl,
                    alt: img.alt
                };
            });

            // add click handlers (don't modify href)
            imageLinks.forEach((link, index) => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    openLightbox(images, index);
                });
            });
        });

        // handle single post page (if no articles, look for post-images directly)
        if (document.querySelectorAll('article').length === 0) {
            const imageLinks = document.querySelectorAll('.post-image a');
            if (imageLinks.length > 0) {
                const images = Array.from(imageLinks).map(link => {
                    const fullUrl = link.href; // use original href as full-size URL
                    const img = link.querySelector('img');
                    return {
                        fullUrl: fullUrl,
                        alt: img.alt
                    };
                });

                imageLinks.forEach((link, index) => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        openLightbox(images, index);
                    });
                });
            }
        }
    }

    // initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeLightbox);
    } else {
        initializeLightbox();
    }
})();