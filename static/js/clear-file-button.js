// handle file input clear buttons
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (!form) return;

    const fileInputs = form.querySelectorAll('input[type="file"]');
    fileInputs.forEach(fileInput => {
        const clearBtn = form.querySelector(`.clear-file-btn[data-target="${fileInput.id}"]`);

        if (clearBtn) {
            // check on page load if file is already selected (Firefox persistence)
            if (fileInput.files.length > 0) {
                clearBtn.style.display = 'block';
            }

            // show/hide clear button based on file selection
            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    clearBtn.style.display = 'block';
                } else {
                    clearBtn.style.display = 'none';
                }
            });

            // clear file input when button is clicked
            clearBtn.addEventListener('click', function() {
                fileInput.value = '';
                clearBtn.style.display = 'none';
            });
        }
    });
});
