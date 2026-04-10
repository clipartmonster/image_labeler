// Function to call get_available_search_batches endpoint
function get_available_search_batches() {
    if (!API_ACCESS_KEY) {
        console.error('API_ACCESS_KEY not available yet. Please wait...');
        return Promise.reject('API_ACCESS_KEY not available');
    }

    // Always get labeler_id from the dropdown select element
    const labelerSelect = document.getElementById('labeler_id');
    
    if (!labelerSelect) {
        console.error('labeler_id dropdown select element not found in DOM');
        return Promise.reject('labeler_id dropdown not found');
    }
    
    const labeler_id = labelerSelect.value;
    
    if (!labeler_id || labeler_id.trim() === '') {
        console.error('labeler_id is empty or not set in dropdown');
        return Promise.reject('labeler_id is required');
    }

    
    const data = {
        'labeler_id': labeler_id
    };

    return api_get_available_search_batches(data);
}

// Function to populate batch dropdown
function populateBatchDropdown(batches) {
    const batchSelect = document.getElementById('batch_id');
    if (!batchSelect) {
        console.error('Batch select dropdown not found');
        return;
    }

    // Preserve the currently selected batch_id before clearing
    const currentBatchId = batchSelect.value;
    
    // Also check URL parameters for batch_id
    const urlParams = new URLSearchParams(window.location.search);
    const batchIdFromUrl = urlParams.get('batch_id');
    
    // Use URL parameter if available, otherwise use current selection
    const batchIdToPreserve = batchIdFromUrl || currentBatchId;

    // Clear existing options
    batchSelect.innerHTML = '';

    if (!batches || !Array.isArray(batches) || batches.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No batches available';
        batchSelect.appendChild(option);
        return;
    }

    // Add each batch as an option
    batches.forEach(function(batch) {
        const option = document.createElement('option');
        option.value = batch.batch_id || batch.id || '';
        // Backend returns search_terms_count, which is the number of search topics left
        const topicsLeft = batch.search_terms_count || batch.number_of_search_topics_left || batch.topics_left || 0;
        option.textContent = `Batch ${batch.batch_id || batch.id} (${topicsLeft} topics left)`;
        batchSelect.appendChild(option);
    });
    
    // Restore the previously selected batch_id if it exists in the new options
    if (batchIdToPreserve) {
        // Check if the batch_id exists in the dropdown
        const optionExists = Array.from(batchSelect.options).some(opt => opt.value === batchIdToPreserve);
        if (optionExists) {
            batchSelect.value = batchIdToPreserve;
        }
    }
}

// Function to handle get_search_term response and update DOM
function handleGetSearchTermResponse(data) {
    // Check if status is error and retry get_search_term
    if (data && data.status === 'error') {
        console.error('Error status from API, retrying get_search_term:', data);
        
        // Get batch_id from the batch dropdown
        const batchSelect = document.getElementById('batch_id');
        const batch_id = batchSelect && batchSelect.value ? batchSelect.value : null;
        
        if (!batch_id) {
            console.error('Cannot retry: no batch_id available');
            window.location.reload();
            return;
        }
        
        // Get labeler_id from dropdown
        const labelerSelect = document.getElementById('labeler_id');
        const labelerId = labelerSelect ? labelerSelect.value : 'Steve';
        
        const searchTermData = {
            batch_id: parseInt(batch_id),
            labeler_id: labelerId
        };
        
        // Retry get_search_term
        api_get_search_term(searchTermData)
            .then(retryData => {
                // Handle the retry response (which may reload the page)
                handleGetSearchTermResponse(retryData);
            })
            .catch(error => {
                console.error('Error retrying get_search_term:', error);
                // If retry fails, reload the page
                window.location.reload();
            });
        return;
    }
    
    // Populate the search string and selected result index fields
    const searchStringInput = document.getElementById('search_string');
    const selectedIndexInput = document.getElementById('selected_result_index');
    
    if (data && !data.error) {
        // Combine search_topic and asset_type into search string
        if (searchStringInput && data.search_topic !== undefined && data.asset_type !== undefined) {
            const combinedString = data.search_topic + ' ' + data.asset_type;
            searchStringInput.value = combinedString;
        }
        
        // Set selected_index into selected result index field
        if (selectedIndexInput && data.selected_index !== undefined) {
            selectedIndexInput.value = data.selected_index;
        }
        
        // Store search_term_id if available
        if (data.id !== undefined) {
            window.searchTermId = data.id;
        }
        
        // Reload the page with the new search parameters after fields are updated
        if (data.search_topic && data.asset_type) {
            const combinedString = data.search_topic + ' ' + data.asset_type;
            
            // Ensure fields are updated first
            if (searchStringInput) {
                searchStringInput.value = combinedString;
            }
            if (selectedIndexInput && data.selected_index !== undefined) {
                selectedIndexInput.value = data.selected_index;
            }
            
            // Build URL with new parameters
            const url = new URL(window.location.href);
            
            // Remove any existing search_term_id parameters (including typos like ssearch_term_id)
            url.searchParams.delete('search_term_id');
            url.searchParams.delete('ssearch_term_id'); // Remove typo if it exists
            
            // Set new parameters
            url.searchParams.set('search_string', combinedString);
            if (data.selected_index !== undefined) {
                url.searchParams.set('selected_result_index', data.selected_index);
            }
            // Store search_term_id in URL (after deleting old ones)
            if (data.id !== undefined) {
                url.searchParams.set('search_term_id', data.id);
            }
            
            // Preserve batch_id from the dropdown
            const batchSelect = document.getElementById('batch_id');
            if (batchSelect && batchSelect.value) {
                url.searchParams.set('batch_id', batchSelect.value);
            }
            
            // Preserve labeler_id from the dropdown
            const labelerSelect = document.getElementById('labeler_id');
            if (labelerSelect && labelerSelect.value) {
                url.searchParams.set('labeler_id', labelerSelect.value);
            }
            
            // Reload the page after fields are populated
            console.log('here')
            window.location.href = url.toString();
        }
    } else if (data && data.error) {
        console.error('Error from API:', data.error);
    }
}

// Function to update search term status to invalid
function api_update_search_term_status(searchTermId) {
    if (!API_ACCESS_KEY) {
        console.error('API_ACCESS_KEY not available yet. Please wait...');
        return Promise.reject('API_ACCESS_KEY not available');
    }

    const apiUrl = 'https://backend-python-nupj.onrender.com/update_search_term_status/';
    
    const requestData = {
        id: searchTermId.toString(),
        status: 'invalid'
    };

    return fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': API_ACCESS_KEY
        },
        body: JSON.stringify(requestData),
        mode: 'cors'
    })
    .then(response => {
        return response.text().then(text => {
            const cleanedText = text.replace(/:\s*NaN\s*([,}])/g, ': null$1');
            return JSON.parse(cleanedText);
        });
    })
    .then(data => {
        console.log('Update Search Term Status Response:', data);
        return data;
    })
    .catch(error => {
        console.error('Error calling update_search_term_status:', error);
        throw error;
    });
}

// Remove listings where images fail to load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize data from json_script elements
    const allSearchResultsElement = document.getElementById('all-search-results-data');
    if (allSearchResultsElement) {
        // Handle NaN values in JSON by replacing them with null
        const cleanedText = allSearchResultsElement.textContent.replace(/:\s*NaN\s*([,}])/g, ': null$1');
        window.allSearchResults = JSON.parse(cleanedText);
    }
    
    // Get current displayed count from the number of listings
    window.currentDisplayedCount = document.querySelectorAll('.asset_view.image_box').length;
    window.replacementIndex = window.currentDisplayedCount;
    
    // Store selected image data
    const selectedImageElement = document.getElementById('selected-image-data');
    if (selectedImageElement) {
        // Handle NaN values in JSON by replacing them with null
        const cleanedText = selectedImageElement.textContent.replace(/:\s*NaN\s*([,}])/g, ': null$1');
        window.selectedImageData = JSON.parse(cleanedText);
    } else {
        window.selectedImageData = null;
    }
    
    // Get search_term_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchTermIdFromUrl = urlParams.get('search_term_id');
    window.searchTermId = searchTermIdFromUrl || null;
    
    // Function to load batches for the current labeler
    function loadBatchesForLabeler() {
        if (!API_ACCESS_KEY) {
            // Wait for API_ACCESS_KEY to be available
            setTimeout(function() {
                loadBatchesForLabeler();
            }, 500);
            return;
        }

        // Ensure dropdown is ready before calling the endpoint
        const labelerSelect = document.getElementById('labeler_id');
        if (!labelerSelect) {
            console.log('Dropdown not ready yet, waiting...');
            setTimeout(function() {
                loadBatchesForLabeler();
            }, 100);
            return;
        }

        // Check if dropdown has a value
        if (!labelerSelect.value || labelerSelect.value.trim() === '') {
            console.log('Dropdown value not set yet, waiting...');
            setTimeout(function() {
                loadBatchesForLabeler();
            }, 100);
            return;
        }

        get_available_search_batches()
            .then(function(batches) {
                // API function now returns the batches array directly
                console.log('Loaded batches:', batches);
                populateBatchDropdown(batches);
            })
            .catch(function(error) {
                console.error('Error loading batches:', error);
                const batchSelect = document.getElementById('batch_id');
                if (batchSelect) {
                    batchSelect.innerHTML = '<option value="">Error loading batches</option>';
                }
            });
    }

    // Load batches on page load
    console.log('Loading batches on page load');
    loadBatchesForLabeler();

    // Reload batches when labeler changes
    const labelerSelect = document.getElementById('labeler_id');
    if (labelerSelect) {
        labelerSelect.addEventListener('change', function() {
            console.log('Labeler changed, reloading batches');
            loadBatchesForLabeler();
        });
    }
    
    // Get Search Term button handler
    const getSearchTermBtn = document.getElementById('get_search_term_btn');
    if (getSearchTermBtn) {
        getSearchTermBtn.addEventListener('click', function() {
            // Add clicked state
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
            
            // Get batch_id from the batch dropdown
            const batchSelect = document.getElementById('batch_id');
            const batch_id = batchSelect && batchSelect.value ? batchSelect.value : null;
            
            if (!batch_id) {
                console.error('Please select a batch first');
                return;
            }
            
            // Get labeler_id from dropdown
            const labelerSelect = document.getElementById('labeler_id');
            const labelerId = labelerSelect ? labelerSelect.value : 'Steve';
            
            console.log('Getting search term for batch_id:', batch_id, 'labeler_id:', labelerId);
            
            const searchTermData = {
                batch_id: parseInt(batch_id),
                labeler_id: labelerId
            };
            
            // Check if API_ACCESS_KEY is available, if not wait a bit
            if (!API_ACCESS_KEY) {
                setTimeout(function() {
                    api_get_search_term(searchTermData)
                        .then(data => {
                            handleGetSearchTermResponse(data);
                        })
                        .catch(error => {
                            console.error('Error getting search term:', error);
                        });
                }, 1000);
            } else {
                api_get_search_term(searchTermData)
                    .then(data => {
                        handleGetSearchTermResponse(data);
                    })
                    .catch(error => {
                        console.error('Error getting search term:', error);
                    });
            }
        });
    }
    
    // Invalid Image button handler
    const invalidImageBtn = document.getElementById('invalid_image_btn');
    if (invalidImageBtn) {
        invalidImageBtn.addEventListener('click', function() {
            // Add clicked state
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
            
            const currentSearchTermId = window.searchTermId;
            if (!currentSearchTermId) {
                console.error('No search term ID available. Please get a search term first.');
                return;
            }
            
            // Get batch_id from the batch dropdown
            const batchSelect = document.getElementById('batch_id');
            const batch_id = batchSelect && batchSelect.value ? batchSelect.value : null;
            
            if (!batch_id) {
                console.error('Please select a batch first');
                return;
            }
            
            // Get labeler_id from dropdown
            const labelerSelect = document.getElementById('labeler_id');
            const labelerId = labelerSelect ? labelerSelect.value : 'Steve';
            
            // Update status to invalid, then get new search term
            api_update_search_term(currentSearchTermId, 'invalid')
                .then(() => {
                    const searchTermData = {
                        batch_id: parseInt(batch_id),
                        labeler_id: labelerId
                    };
                    return api_get_search_term(searchTermData);
                })
                .then(data => {
                    handleGetSearchTermResponse(data);
                })
                .catch(error => {
                    console.error('Error updating search term status or getting new search term:', error);
                });
        });
    }
    
    // Select All button handler (toggles between select all and unselect all)
    const selectAllBtn = document.getElementById('select_all_btn');
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            // Add clicked state
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
            
            const allListings = document.querySelectorAll('.asset_view.image_box');
            
            // Check if all listings are already selected
            const allSelected = Array.from(allListings).every(function(container) {
                return container.classList.contains('selected');
            });
            
            if (allSelected) {
                // Unselect all
                allListings.forEach(function(container) {
                    container.classList.remove('selected');
                });
                console.log(`Unselected all ${allListings.length} listings`);
            } else {
                // Select all
                allListings.forEach(function(container) {
                    container.classList.add('selected');
                });
                console.log(`Selected all ${allListings.length} listings`);
            }
        });
    }
    
    // Search form button clicked state
    const searchForm = document.querySelector('.search_form_container form');
    if (searchForm) {
        const searchSubmitBtn = searchForm.querySelector('button[type="submit"]');
        if (searchSubmitBtn) {
            searchSubmitBtn.addEventListener('click', function() {
                this.classList.add('clicked');
                setTimeout(() => this.classList.remove('clicked'), 300);
            });
        }
    }
    
    // Identical button handlers
    const identicalButtons = document.querySelectorAll('.identical_btn');
    identicalButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent triggering the container click
            
            // Add clicked state
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
            
            const container = this.closest('.asset_view.image_box');
            if (container) {
                // Toggle identical state
                if (container.classList.contains('identical')) {
                    container.classList.remove('identical');
                    container.classList.remove('selected'); // Also remove selected if present
                } else {
                    container.classList.add('identical');
                    container.classList.remove('selected'); // Remove selected if present
                }
            }
        });
    });
    
    // Function to zoom an image
    function zoomImage(img) {
        if (img.classList.contains('zoomed')) {
            img.classList.remove('zoomed');
            img.style.transform = '';
            img.style.transformOrigin = '';
        } else {
            img.classList.add('zoomed');
            img.style.transform = 'scale(2)';
            img.style.transformOrigin = 'top left';
        }
    }
    
    // Function to close all zoomed images
    function closeAllZooms() {
        const zoomedImages = document.querySelectorAll('img.zoomed');
        zoomedImages.forEach(function(img) {
            img.classList.remove('zoomed');
            img.style.transform = '';
        });
    }
    
    // Track if we should ignore the next click (to prevent immediate closing after zoom button click)
    let ignoreNextClick = false;
    
    // Zoom button handlers for listing images
    const listingZoomButtons = document.querySelectorAll('.listing_zoom');
    listingZoomButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent triggering the container click
            e.stopImmediatePropagation(); // Prevent other handlers
            
            ignoreNextClick = true;
            setTimeout(function() {
                ignoreNextClick = false;
            }, 100);
            
            const container = this.closest('.asset_view.image_box');
            if (container) {
                const img = container.querySelector('img.design.view_asset_labels.large');
                if (img) {
                    zoomImage(img);
                }
            }
        });
    });
    
    // Zoom button handler for selected image
    const selectedImageZoomBtn = document.querySelector('.selected_image_zoom');
    if (selectedImageZoomBtn) {
        selectedImageZoomBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            ignoreNextClick = true;
            setTimeout(function() {
                ignoreNextClick = false;
            }, 100);
            
            const selectedImageContainer = this.closest('.selected_image.container');
            if (selectedImageContainer) {
                const img = selectedImageContainer.querySelector('img.selected_image_img');
                if (img) {
                    zoomImage(img);
                }
            }
        });
    }
    
    // Close zoom when clicking anywhere (except on zoom buttons)
    // Use capturing phase to catch clicks before they reach listing containers
    document.addEventListener('click', function(e) {
        // Don't close if clicking on a zoom button or its SVG, or if we should ignore this click
        if (e.target.closest('.zoom_magnify_btn') || ignoreNextClick) {
            return;
        }
        
        // Check if there are any zoomed images
        const zoomedImages = document.querySelectorAll('img.zoomed');
        if (zoomedImages.length > 0) {
            // Close all zoomed images and prevent other handlers
            e.stopPropagation();
            e.stopImmediatePropagation();
            closeAllZooms();
            return false;
        }
    }, true); // Use capturing phase
    
    // Make listings clickable and toggle orange background
    const listingContainers = document.querySelectorAll('.asset_view.image_box');
    
    listingContainers.forEach(function(container) {
        container.addEventListener('click', function(e) {
            // Don't toggle if clicking on the identical button or zoom button
            if (e.target.classList.contains('identical_btn') || e.target.closest('.zoom_magnify_btn')) {
                return;
            }
            
            // Don't toggle if there are zoomed images (let the document click handler close them first)
            const zoomedImages = document.querySelectorAll('img.zoomed');
            if (zoomedImages.length > 0) {
                return;
            }
            
            // Toggle the 'selected' class
            if (this.classList.contains('selected')) {
                this.classList.remove('selected');
            } else {
                this.classList.remove('identical'); // Remove identical if selecting
                this.classList.add('selected');
            }
        });
    });
    
    // Function to replace a failed listing with the next available one
    function replaceFailedListing(container) {
        if (typeof window.allSearchResults === 'undefined' || !window.allSearchResults || window.replacementIndex >= window.allSearchResults.length) {
            // No more replacements available, just remove it
            container.remove();
            return;
        }
        
        const replacementAsset = window.allSearchResults[window.replacementIndex];
        window.replacementIndex++;
        
        if (!replacementAsset || !replacementAsset.image_link) {
            // Skip if no image link, try next one
            replaceFailedListing(container);
            return;
        }
        
        // Get the asset_id from the container
        const assetId = container.getAttribute('asset_id');
        
        // Update the container with new asset data
        container.setAttribute('asset_id', replacementAsset.asset_id);
        container.setAttribute('id', 'container_' + replacementAsset.asset_id);
        
        // Update asset_id display
        const assetIdLabel = container.querySelector('h2.label_option.label');
        if (assetIdLabel && assetIdLabel.textContent.trim() === assetId.toString()) {
            assetIdLabel.textContent = replacementAsset.asset_id;
        }
        
        // Update the image
        const img = container.querySelector('img.design.view_asset_labels.large');
        if (img) {
            img.setAttribute('id', 'image_' + replacementAsset.asset_id);
            
            // Set new image source (matching template logic)
            let imageSrc = replacementAsset.image_link;
            if (imageSrc) {
                if (imageSrc.startsWith('https://')) {
                    // Use proxy for https URLs
                    const urlWithoutProtocol = imageSrc.substring(8);
                    imageSrc = 'https://images.weserv.nl/?url=' + encodeURIComponent(urlWithoutProtocol);
                } else if (imageSrc.startsWith('http://')) {
                    // Use proxy for http URLs
                    const urlWithoutProtocol = imageSrc.substring(7);
                    imageSrc = 'https://images.weserv.nl/?url=' + encodeURIComponent(urlWithoutProtocol);
                }
            }
            img.src = imageSrc;
            img.crossOrigin = 'anonymous';
            
            // Reset error state
            img.onerror = null;
            
            // Add new error handler
            img.addEventListener('error', function() {
                replaceFailedListing(container);
            });
        }
        
        // Update agree_status if present
        const agreeStatusLabels = container.querySelectorAll('h2.label_option.label');
        if (agreeStatusLabels.length > 1 && replacementAsset.agree_status !== undefined) {
            agreeStatusLabels[agreeStatusLabels.length - 1].textContent = replacementAsset.agree_status || '';
        }
    }
    
    // Find all listing images
    const listingImages = document.querySelectorAll('img.design.view_asset_labels.large');
    
    listingImages.forEach(function(img) {
        // Add error handler to replace the listing container if image fails to load
        img.addEventListener('error', function() {
            // Find the parent container (asset_view image_box)
            const container = img.closest('.asset_view.image_box');
            if (container) {
                replaceFailedListing(container);
            }
        });
        
        // Also check if image is already broken (naturalWidth === 0)
        if (img.complete && img.naturalWidth === 0) {
            const container = img.closest('.asset_view.image_box');
            if (container) {
                replaceFailedListing(container);
            }
        }
    });
    
    // Submit button handler
    const submitBtn = document.getElementById('submit_btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent form submission if inside a form
            
            if (!API_ACCESS_KEY) {
                console.error('API_ACCESS_KEY not available yet. Please wait...');
                return;
            }
            
            // Get all listing containers
            const listingContainers = document.querySelectorAll('.asset_view.image_box');
            
            if (listingContainers.length === 0) {
                console.log('No listings to submit');
                return;
            }
            
            // Get search_term_id from URL or global variable
            const urlParams = new URLSearchParams(window.location.search);
            const searchTermIdFromUrl = urlParams.get('search_term_id');
            const currentSearchTermId = searchTermIdFromUrl || (typeof window.searchTermId !== 'undefined' ? window.searchTermId : null);
            
            if (!currentSearchTermId) {
                console.error('No search term ID available. Please get a search term first.');
                return;
            }
            
            // Get selected image asset_id (the main image in the left panel)
            const selectedImage = typeof window.selectedImageData !== 'undefined' ? window.selectedImageData : null;
            let selectedAssetId = selectedImage && selectedImage.asset_id 
                ? selectedImage.asset_id.toString() 
                : null;
            
            // Get labeler_id from dropdown menu
            const labelerSelect = document.getElementById('labeler_id');
            const labelerId = labelerSelect ? labelerSelect.value : 'Steve'; // Default to 'Steve' if dropdown not found
            
            // Process each listing sequentially (one at a time)
            const listings = [];
            listingContainers.forEach(function(container) {
                const listingAssetId = container.getAttribute('asset_id');
                
                if (!listingAssetId) {
                    console.warn('Listing container missing asset_id, skipping');
                    return;
                }
                
                // Check container state: identical (purple), selected (orange), or no (default)
                const isIdentical = container.classList.contains('identical');
                const isSelected = container.classList.contains('selected');
                
                let responseValue;
                if (isIdentical) {
                    responseValue = 'identical';
                } else if (isSelected) {
                    responseValue = 'yes';
                } else {
                    responseValue = 'no';
                }
                
                listings.push({
                    listingAssetId: listingAssetId.toString(),
                    responseValue: responseValue
                });
            });
            
            // If no selected image asset_id, use the first listing's asset_id as fallback
            if (!selectedAssetId && listings.length > 0) {
                selectedAssetId = listings[0].listingAssetId;
                console.log(`No selected image available. Using first listing's asset_id as selected_asset_id: ${selectedAssetId}`);
            }
            
            if (!selectedAssetId) {
                console.error('No selected asset ID available and no listings found.');
                alert('No listings available to submit.');
                return;
            }
            
            // Function to submit a single listing
            function submitListing(listing, index) {
                const apiUrl = 'https://backend-python-nupj.onrender.com/update_search_result_response/';
                
                const requestData = {
                    id: currentSearchTermId.toString(),
                    labeler_id: labelerId,
                    response: listing.responseValue,
                    selected_asset_id: selectedAssetId || null, // Can be null if no selected image
                    listing_asset_id: listing.listingAssetId
                };
                
                console.log(`Submitting listing ${index + 1}/${listings.length}:`);
                console.log(`  - Selected Asset ID: ${selectedAssetId}`);
                console.log(`  - Listing Asset ID: ${listing.listingAssetId}`);
                console.log(`  - Are they the same? ${selectedAssetId === listing.listingAssetId}`);
                console.log(`  - Full request:`, requestData);
                
                return fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': API_ACCESS_KEY
                    },
                    body: JSON.stringify(requestData),
                    mode: 'cors'
                })
                .then(fetchResponse => {
                    // Get response as text first to handle potential NaN values
                    return fetchResponse.text().then(text => {
                        // Try to parse as JSON
                        let responseData;
                        try {
                            // Replace NaN with null to make it valid JSON if needed
                            const cleanedText = text.replace(/:\s*NaN\s*([,}])/g, ': null$1');
                            responseData = JSON.parse(cleanedText);
                        } catch (e) {
                            // If not JSON, use the text as is
                            responseData = { raw_response: text };
                        }
                        
                        // Check HTTP status
                        if (!fetchResponse.ok) {
                            throw new Error(`HTTP error! status: ${fetchResponse.status}, response: ${JSON.stringify(responseData)}`);
                        }
                        
                        // Check API response status
                        if (responseData.status === 'failed') {
                            throw new Error(`API error: ${responseData.explanation || 'Unknown error'}`);
                        }
                        
                        // Log what happened (created vs updated)
                        const action = responseData.explanation && responseData.explanation.includes('Created') ? 'CREATED' : 'UPDATED';
                        console.log(`[${action}] Listing ${listing.listingAssetId}: response=${listing.responseValue}`);
                        console.log(`  - API Response:`, responseData);
                        if (responseData.updated_count !== undefined) {
                            console.warn(`  - WARNING: Updated ${responseData.updated_count} entries (should be 1 per listing)`);
                        }
                        if (responseData.total_matching_entries !== undefined) {
                            console.warn(`  - WARNING: Found ${responseData.total_matching_entries} matching entries`);
                        }
                        
                        return { listingAssetId: listing.listingAssetId, response: listing.responseValue, success: true, apiResponse: responseData, action: action };
                    });
                })
                .catch(error => {
                    console.error(`Error submitting listing ${listing.listingAssetId}:`, error);
                    console.error('Request data was:', requestData);
                    return { listingAssetId: listing.listingAssetId, response: listing.responseValue, success: false, error: error.message };
                });
            }
            
            // Process listings sequentially (one at a time)
            const results = [];
            let currentIndex = 0;
            
            function processNext() {
                if (currentIndex >= listings.length) {
                    // All done
                    const successful = results.filter(r => r.success).length;
                    const failed = results.filter(r => !r.success).length;
                    const created = results.filter(r => r.success && r.action === 'CREATED').length;
                    const updated = results.filter(r => r.success && r.action === 'UPDATED').length;
                    
                    console.log(`\n=== Submission Summary ===`);
                    console.log(`Total listings: ${listings.length}`);
                    console.log(`Successful: ${successful}`);
                    console.log(`Failed: ${failed}`);
                    console.log(`Created: ${created}`);
                    console.log(`Updated: ${updated}`);
                    console.log(`\n⚠️  WARNING: If Updated count is high, the endpoint may be updating the same entry multiple times instead of creating separate entries for each listing.`);
                    
                    // Remove all listings from the DOM
                    const allListings = document.querySelectorAll('.asset_view.image_box');
                    allListings.forEach(function(listing) {
                        listing.remove();
                    });
                    
                    // Log message to console
                    if (failed === 0) {
                        console.log(`Successfully submitted ${successful} listings!\nCreated: ${created}\nUpdated: ${updated}`);
                    } else {
                        console.log(`Submitted ${successful} listings, ${failed} failed.\nCreated: ${created}\nUpdated: ${updated}\n\nCheck console for details.`);
                    }
                    
                    // Get a new search term after alert is dismissed
                    // Get batch_id from the batch dropdown
                    const batchSelect = document.getElementById('batch_id');
                    const batch_id = batchSelect && batchSelect.value ? batchSelect.value : null;

                    if (batch_id) {
                        const searchTermData = {
                            batch_id: batch_id,
                            labeler_id: labelerId
                        };
                        api_get_search_term(searchTermData)
                            .then(data => {
                                handleGetSearchTermResponse(data);
                            })
                            .catch(error => {
                                console.error('Error getting new search term:', error);
                                // Don't show alert here as user just dismissed one
                            });
                    } else {
                        console.warn('No batch_id selected, cannot get new search term');
                    }
                    return;
                }
                
                const listing = listings[currentIndex];
                submitListing(listing, currentIndex)
                    .then(result => {
                        results.push(result);
                        currentIndex++;
                        // Process next listing after a short delay to avoid overwhelming the server
                        setTimeout(processNext, 100);
                    })
                    .catch(error => {
                        results.push({ listingAssetId: listing.listingAssetId, success: false, error: error.message });
                        currentIndex++;
                        setTimeout(processNext, 100);
                    });
            }
            
            // Start processing
            processNext();
        });
    }
});
