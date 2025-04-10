// Main JavaScript for University Timetable Scheduler - Enhanced Version

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips from Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alert messages after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        });
    }, 5000);

    // Handle tab persistence through page reloads
    var activeTabID = localStorage.getItem('activeTab');
    if (activeTabID) {
        var triggerEl = document.querySelector('button[data-bs-target="' + activeTabID + '"]');
        if (triggerEl) {
            var tab = new bootstrap.Tab(triggerEl);
            tab.show();
        }
    }

    // Store active tab when changed
    var tabElList = [].slice.call(document.querySelectorAll('button[data-bs-toggle="tab"]'));
    tabElList.forEach(function(tabEl) {
        tabEl.addEventListener('shown.bs.tab', function(event) {
            localStorage.setItem('activeTab', event.target.getAttribute('data-bs-target'));
        });
    });

    // Add animation classes to elements as they scroll into view
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const screenPosition = window.innerHeight;
            
            if (elementPosition < screenPosition - 100) {
                if (element.classList.contains('fade-in-up')) {
                    element.classList.add('animated');
                } else if (element.classList.contains('fade-in-left')) {
                    element.classList.add('animated');
                } else if (element.classList.contains('fade-in-right')) {
                    element.classList.add('animated');
                } else if (element.classList.contains('zoom-in')) {
                    element.classList.add('animated');
                } else {
                    element.classList.add('fade-in');
                }
            }
        });
    };

    // Run animation check on load and scroll
    window.addEventListener('scroll', animateOnScroll);
    window.addEventListener('load', animateOnScroll);

    // Filter functionality for tables with search
    const searchInputs = document.querySelectorAll('input[id$="-search"]');
    if (searchInputs.length > 0) {
        searchInputs.forEach(function(input) {
            input.addEventListener('keyup', function() {
                const searchTerm = this.value.toLowerCase();
                const rowClass = this.id.replace('-search', '-row');
                const rows = document.querySelectorAll('.' + rowClass);
                
                let visibleCount = 0;
                rows.forEach(function(row) {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Show no results message if needed
                const noResultsMsg = document.getElementById(this.id.replace('-search', '-no-results'));
                if (noResultsMsg) {
                    noResultsMsg.style.display = visibleCount === 0 ? 'block' : 'none';
                }
            });
        });
    }

    // Confirmation for dangerous actions
    document.querySelectorAll('.confirm-action').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to perform this action? It cannot be undone.')) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // Add active class to current page in navbar
    const currentLocation = location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
            
            // If in dropdown, also highlight parent
            const dropdownParent = link.closest('.dropdown');
            if (dropdownParent) {
                const dropdownToggle = dropdownParent.querySelector('.dropdown-toggle');
                if (dropdownToggle) {
                    dropdownToggle.classList.add('active');
                }
            }
        }
    });
    
    // Interactive timetable - highlight related courses on hover
    const courseElements = document.querySelectorAll('[data-course-id]');
    if (courseElements.length > 0) {
        courseElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                const courseId = this.getAttribute('data-course-id');
                document.querySelectorAll(`[data-course-id="${courseId}"]`).forEach(el => {
                    el.classList.add('highlight-course');
                });
            });
            
            element.addEventListener('mouseleave', function() {
                const courseId = this.getAttribute('data-course-id');
                document.querySelectorAll(`[data-course-id="${courseId}"]`).forEach(el => {
                    el.classList.remove('highlight-course');
                });
            });
        });
    }
    
    // Dark mode toggle functionality
    const darkModeToggle = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    
    // Check for saved dark mode preference
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        htmlElement.setAttribute('data-bs-theme', 'dark');
        darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    // Toggle dark mode
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            if (htmlElement.getAttribute('data-bs-theme') === 'dark') {
                htmlElement.removeAttribute('data-bs-theme');
                localStorage.setItem('darkMode', 'false');
                darkModeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            } else {
                htmlElement.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('darkMode', 'true');
                darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            }
        });
    }
    
    // Handle PDF upload form document type selection
    const documentTypeSelect = document.getElementById('document_type');
    const courseSelector = document.querySelector('.course-selector');
    
    if (documentTypeSelect && courseSelector) {
        documentTypeSelect.addEventListener('change', function() {
            if (this.value === 'course_material') {
                courseSelector.style.display = 'block';
                document.getElementById('pdf_course_id').setAttribute('required', '');
            } else {
                courseSelector.style.display = 'none';
                document.getElementById('pdf_course_id').removeAttribute('required');
            }
        });
    }
    
    // Upload modal functionality
    const uploadModal = document.getElementById('uploadModal');
    const uploadButton = document.getElementById('upload-button');
    
    // If upload button doesn't exist yet but modal does, create the button
    if (!uploadButton && uploadModal) {
        const navbarNav = document.querySelector('.navbar-nav');
        if (navbarNav) {
            // Create upload button list item
            const uploadListItem = document.createElement('li');
            uploadListItem.className = 'nav-item';
            
            // Create upload button
            const uploadLink = document.createElement('a');
            uploadLink.className = 'nav-link';
            uploadLink.href = '#';
            uploadLink.id = 'upload-button';
            uploadLink.innerHTML = '<i class="fas fa-upload me-1"></i> Upload';
            
            // Add to navbar
            uploadListItem.appendChild(uploadLink);
            navbarNav.appendChild(uploadListItem);
            
            // Add click event
            uploadLink.addEventListener('click', function(e) {
                e.preventDefault();
                const modalInstance = new bootstrap.Modal(uploadModal);
                modalInstance.show();
            });
        }
    }
    
    // Handle file uploads with preview
    const fileInput = document.getElementById('fileUpload');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                const fileInfoElement = document.querySelector('.file-info');
                if (fileInfoElement) {
                    fileInfoElement.textContent = 'Selected file: ' + fileName;
                    fileInfoElement.classList.add('text-success');
                }
                
                // Show preview if it's a CSV
                if (fileName.toLowerCase().endsWith('.csv')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const contents = e.target.result;
                        const previewElement = document.querySelector('.file-preview');
                        if (previewElement) {
                            // Show first few lines of the CSV
                            const lines = contents.split('\n').slice(0, 5);
                            previewElement.innerHTML = '<div class="mt-3"><strong>Preview:</strong><pre class="bg-light p-2 rounded mt-2" style="max-height: 150px; overflow-y: auto;">' + 
                                lines.join('\n') + '\n...' + '</pre></div>';
                        }
                    };
                    reader.readAsText(this.files[0]);
                }
            }
        });
    }
    
    // Add counter animations to stat numbers
    const animateCounters = () => {
        document.querySelectorAll('.counter-animation').forEach(counter => {
            const target = parseInt(counter.getAttribute('data-target'));
            const duration = 1500; // Animation duration in milliseconds
            const startTime = performance.now();
            
            const updateCounter = (currentTime) => {
                const elapsedTime = currentTime - startTime;
                const progress = Math.min(elapsedTime / duration, 1);
                const easedProgress = -Math.cos(progress * Math.PI) / 2 + 0.5; // Ease in-out
                const currentValue = Math.floor(easedProgress * target);
                
                counter.textContent = currentValue;
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target;
                }
            };
            
            requestAnimationFrame(updateCounter);
        });
    };
    
    // Run counter animations when elements come into view
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                counterObserver.disconnect(); // Only run once
            }
        });
    }, { threshold: 0.1 });
    
    const counterElements = document.querySelector('.counter-animation');
    if (counterElements) {
        counterObserver.observe(counterElements);
    }
    
    // Add parallax effect to cards
    const cards = document.querySelectorAll('.parallax-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left; // x position within the element
            const y = e.clientY - rect.top; // y position within the element
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const deltaX = (x - centerX) / centerX * 10; // Max 10 degrees
            const deltaY = (y - centerY) / centerY * 10; // Max 10 degrees
            
            card.style.transform = `perspective(1000px) rotateX(${-deltaY}deg) rotateY(${deltaX}deg) scale3d(1.05, 1.05, 1.05)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
        });
    });
}); 