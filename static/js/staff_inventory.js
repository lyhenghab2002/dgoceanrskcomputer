

    // Get user role from session
function getUserRole() {
    // This will be set by the template
    return window.userRole || 'staff';
}

document.addEventListener('DOMContentLoaded', () => {
   
    const addProductBtn = document.getElementById('add-product-btn');
    const closeModalButtons = document.querySelectorAll('.close-modal');
    
    const inventoryTableBody = document.getElementById('inventory-table-body');
    const mobileInventoryList = document.getElementById('mobile-inventory-list');
    const searchInput = document.getElementById('search-products');
    const refreshBtn = document.getElementById('refresh-btn');

    // Hide Add Product button for staff users
    if (getUserRole() === 'staff' && addProductBtn) {
        addProductBtn.style.display = 'none';
    }
    const paginationContainer = document.getElementById('pagination');

    let currentPage = 1;
    let pageSize = 10;
    let sortBy = 'id';
    let sortDir = 'desc';
    let currentQuery = '';
    let currentCategoryFilter = '';
    let currentBrandFilter = '';
    let currentStockFilter = '';

    let selectedFiles = [null, null, null];
    const labels = ['Main Image', 'Back View', 'Left Rear View'];
    let editSelectedFiles = [null, null, null];
    const editLabels = ['Main Image', 'Back View', 'Left Rear View'];

    // Initialize pagination counter elements
    const paginationInfo = document.getElementById('pagination-info');
    const itemRange = document.getElementById('item-range');

    const imagesInput = document.getElementById('product-images');
    const previewContainer = document.getElementById('image-preview-container');
    const editImagesInput = document.getElementById('edit-product-images');
    const editPreviewContainer = document.getElementById('edit-image-preview-container');

    // Modern image preview handling
    function updatePreviews() {
        const previewImagesDiv = previewContainer.querySelector('.preview-images');
        previewImagesDiv.innerHTML = '';

        const hasAnyFile = selectedFiles.some(file => file !== null);
        if (!hasAnyFile) {
            previewContainer.style.display = 'none';
            return;
        }

        previewContainer.style.display = 'block';
        selectedFiles.forEach((file, index) => {
            if (file) {
                const reader = new FileReader();
                reader.onload = function(readerEvent) {
                    const previewDiv = document.createElement('div');
                    previewDiv.className = 'preview-image';
                    previewDiv.innerHTML = `
                        <img src="${readerEvent.target.result}" alt="${labels[index]}">
                        <div class="image-label">${labels[index]}</div>
                        <button type="button" class="remove-btn" onclick="removeImage(${index})" title="Remove image">×</button>
                    `;
                    previewImagesDiv.appendChild(previewDiv);
                };
                reader.readAsDataURL(file);
            }
        });
    }

    function updateEditPreviews() {
        const editPreviewImagesDiv = editPreviewContainer.querySelector('.preview-images');
        editPreviewImagesDiv.innerHTML = '';

        const hasAnyFile = editSelectedFiles.some(file => file !== null);
        if (!hasAnyFile) {
            editPreviewContainer.style.display = 'none';
            return;
        }

        editPreviewContainer.style.display = 'block';
        editSelectedFiles.forEach((file, index) => {
            if (file) {
                const reader = new FileReader();
                reader.onload = function(readerEvent) {
                    const previewDiv = document.createElement('div');
                    previewDiv.className = 'preview-image';
                    previewDiv.innerHTML = `
                        <img src="${readerEvent.target.result}" alt="${editLabels[index]}">
                        <div class="image-label">${editLabels[index]}</div>
                        <button type="button" class="remove-btn" onclick="removeEditImage(${index})" title="Remove image">×</button>
                    `;
                    editPreviewImagesDiv.appendChild(previewDiv);
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Image selection handlers
    if (imagesInput && previewContainer) {
        const previewImagesDiv = previewContainer.querySelector('.preview-images');
        imagesInput.setAttribute('multiple', 'multiple');

        imagesInput.addEventListener('change', function(e) {
            let files = Array.from(e.target.files);
            if (files.length === 0) return;

            if (files.length > 3) {
                showMessage('Maximum 3 images allowed. Only the first 3 will be used.', 'warning');
                files = files.slice(0, 3);
            }

            let fileIndex = 0;
            const currentCount = selectedFiles.filter(file => file !== null).length;

            if (files.length === 1 && currentCount > 0) {
                for (let slotIndex = 0; slotIndex < 3 && fileIndex < files.length; slotIndex++) {
                    if (selectedFiles[slotIndex] === null) {
                        const file = files[fileIndex];
                        if (file.type.startsWith('image/')) {
                            selectedFiles[slotIndex] = file;
                            fileIndex++;
                            break;
                        } else {
                            showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                            fileIndex++;
                        }
                    }
                }
            } else {
                for (let slotIndex = 0; slotIndex < 3 && fileIndex < files.length; slotIndex++) {
                    const file = files[fileIndex];
                    if (file.type.startsWith('image/')) {
                        selectedFiles[slotIndex] = file;
                        fileIndex++;
                    } else {
                        showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                        fileIndex++;
                    }
                }
            }

            updatePreviews();
            syncMultipleSelectionInput();
            e.target.value = '';
        });

        window.removeImage = function(index) {
            selectedFiles[index] = null;
            updatePreviews();
            syncMultipleSelectionInput();
        };

        window.replaceImage = function(index) {
            const tempInput = document.createElement('input');
            tempInput.type = 'file';
            tempInput.accept = 'image/*';
            tempInput.style.display = 'none';
            tempInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    selectedFiles[index] = file;
                    updatePreviews();
                    syncMultipleSelectionInput();
                } else if (file) {
                    showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                }
                document.body.removeChild(tempInput);
            });
            document.body.appendChild(tempInput);
            tempInput.click();
        };

        function syncMultipleSelectionInput() {
            const dt = new DataTransfer();
            selectedFiles.forEach(file => {
                if (file) dt.items.add(file);
            });
            imagesInput.files = dt.files;
        }
    }

    if (editImagesInput && editPreviewContainer) {
        const editPreviewImagesDiv = editPreviewContainer.querySelector('.preview-images');
        editImagesInput.setAttribute('multiple', 'multiple');

        editImagesInput.addEventListener('change', function(e) {
            let files = Array.from(e.target.files);
            if (files.length === 0) return;

            if (files.length > 3) {
                showMessage('Maximum 3 images allowed. Only the first 3 will be used.', 'warning');
                files = files.slice(0, 3);
            }

            let fileIndex = 0;
            const currentCount = editSelectedFiles.filter(file => file !== null).length;

            if (files.length === 1 && currentCount > 0) {
                for (let slotIndex = 0; slotIndex < 3 && fileIndex < files.length; slotIndex++) {
                    if (editSelectedFiles[slotIndex] === null) {
                        const file = files[fileIndex];
                        if (file.type.startsWith('image/')) {
                            editSelectedFiles[slotIndex] = file;
                            fileIndex++;
                            break;
                        } else {
                            showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                            fileIndex++;
                        }
                    }
                }
            } else {
                for (let slotIndex = 0; slotIndex < 3 && fileIndex < files.length; slotIndex++) {
                    const file = files[fileIndex];
                    if (file.type.startsWith('image/')) {
                        editSelectedFiles[slotIndex] = file;
                        fileIndex++;
                    } else {
                        showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                        fileIndex++;
                    }
                }
            }

            updateEditPreviews();
            syncEditMultipleSelectionInput();
            e.target.value = '';
        });

        window.removeEditImage = function(index) {
            editSelectedFiles[index] = null;
            updateEditPreviews();
            syncEditMultipleSelectionInput();
        };

        window.replaceEditImage = function(index) {
            const tempInput = document.createElement('input');
            tempInput.type = 'file';
            tempInput.accept = 'image/*';
            tempInput.style.display = 'none';
            tempInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    editSelectedFiles[index] = file;
                    updateEditPreviews();
                    syncEditMultipleSelectionInput();
                } else if (file) {
                    showMessage(`File "${file.name}" is not a valid image file.`, 'error');
                }
                document.body.removeChild(tempInput);
            });
            document.body.appendChild(tempInput);
            tempInput.click();
        };

        function syncEditMultipleSelectionInput() {
            const dt = new DataTransfer();
            editSelectedFiles.forEach(file => {
                if (file) dt.items.add(file);
            });
            editImagesInput.files = dt.files;
        }
    }

   

        closeModalButtons.forEach(button => {
            button.addEventListener('click', () => {
                
                document.getElementById('product-detail-modal').classList.remove('show-slide');
                clearEditModalImages();
            });
        });

    function clearEditModalImages() {
        editSelectedFiles = [null, null, null];
        if (editPreviewContainer) {
            editPreviewContainer.style.display = 'none';
            editPreviewImagesDiv.innerHTML = '';
        }
        if (editImagesInput) {
            editImagesInput.value = '';
        }
    }

    
    // Fetch inventory with loading state and request deduplication
    let isLoading = false;
    let currentRequest = null;
    let cache = new Map();
    let cacheTimeout = 300000; // 5 minutes cache for instant loading
    let paginationCache = new Map(); // Separate cache for pagination
    let paginationCacheTimeout = 600000; // 10 minutes for pagination cache
    let preloadedPages = new Set(); // Track preloaded pages
    let isPreloading = false;
    
    async function fetchInventory(page = currentPage) {
        // Prevent multiple simultaneous requests
        if (isLoading) {
            console.log('Request already in progress, skipping...');
            return;
        }
        
        // Cancel previous request if it's still pending
        if (currentRequest) {
            currentRequest.abort();
        }
        
        isLoading = true;
        currentPage = page;
        
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const productId = urlParams.get('product_id');
            let url = `/staff/inventory/search?page=${currentPage}&page_size=${pageSize}&sort_by=${sortBy}&sort_dir=${sortDir}`;
            if (productId) url += `&product_id=${encodeURIComponent(productId)}`;
            if (currentBrandFilter) url += `&brand_filter=${encodeURIComponent(currentBrandFilter)}`;
            if (currentCategoryFilter) url += `&category_filter=${encodeURIComponent(currentCategoryFilter)}`;
            if (currentStockFilter) url += `&stock_filter=${encodeURIComponent(currentStockFilter)}`;
            if (currentQuery) url += `&q=${encodeURIComponent(currentQuery)}`;

            // Check cache first - use pagination cache for page navigation
            const cacheKey = url;
            const isPaginationRequest = page !== 1;
            const cacheToUse = isPaginationRequest ? paginationCache : cache;
            const cacheTimeoutToUse = isPaginationRequest ? paginationCacheTimeout : cacheTimeout;
            
            const cached = cacheToUse.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < cacheTimeoutToUse) {
                console.log(`⚡ INSTANT: Using ${isPaginationRequest ? 'pagination' : 'regular'} cached data for page ${page}`);
                // Instant rendering for cached data
                renderInventory(cached.data.products, cached.data.pagination);
                renderPagination(cached.data.pagination.total_count, currentPage);
                updateItemCounter(cached.data.pagination);
                isLoading = false;
                
                // Preload adjacent pages for instant navigation
                preloadAdjacentPages(cached.data.pagination.total_count, page);
                return;
            }

            // Show loading state only for non-cached requests
            if (inventoryTableBody) {
                inventoryTableBody.innerHTML = '<tr><td colspan="10" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading products...</td></tr>';
            }
            if (mobileInventoryList) {
                mobileInventoryList.innerHTML = '<p class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading products...</p>';
            }

            // Create abortable request with timeout
            const controller = new AbortController();
            currentRequest = controller;
            
            // Set a timeout for the request
            const timeoutId = setTimeout(() => {
                controller.abort();
            }, 10000); // 10 second timeout
            
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            clearTimeout(timeoutId);
            const data = await response.json();
            
            if (data.success) {
                // Cache the result in appropriate cache
                cacheToUse.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
                
                console.log(`Cached ${isPaginationRequest ? 'pagination' : 'regular'} data for page ${page}`);
                
                // Instant rendering
                renderInventory(data.products, data.pagination);
                renderPagination(data.pagination.total_count, currentPage);
                updateItemCounter(data.pagination);
                
                // Preload adjacent pages for instant navigation
                preloadAdjacentPages(data.pagination.total_count, page);
            } else {
                inventoryTableBody.innerHTML = '<tr><td colspan="10">Error loading inventory.</td></tr>';
                mobileInventoryList.innerHTML = '<p>Error loading inventory.</p>';
                paginationContainer.innerHTML = '';
                updateItemCounter({ total_count: 0, page: 1, total_pages: 0 });
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request was aborted or timed out');
                inventoryTableBody.innerHTML = '<tr><td colspan="10" class="text-center text-warning">Request timed out. Please try again.</td></tr>';
                mobileInventoryList.innerHTML = '<p class="text-center text-warning">Request timed out. Please try again.</p>';
                return;
            }
            console.error('Error:', error);
            inventoryTableBody.innerHTML = '<tr><td colspan="10">Error loading inventory.</td></tr>';
            mobileInventoryList.innerHTML = '<p>Error loading inventory.</p>';
            paginationContainer.innerHTML = '';
            updateItemCounter({ total_count: 0, page: 1, total_pages: 0 });
        } finally {
            isLoading = false;
            currentRequest = null;
        }
    }

    // Preload adjacent pages for instant navigation
    async function preloadAdjacentPages(totalPages, currentPage) {
        if (isPreloading) return;
        
        const pagesToPreload = [];
        
        // Preload previous page
        if (currentPage > 1) {
            pagesToPreload.push(currentPage - 1);
        }
        
        // Preload next page
        if (currentPage < totalPages) {
            pagesToPreload.push(currentPage + 1);
        }
        
        // Preload pages 2-3 if on page 1
        if (currentPage === 1 && totalPages > 1) {
            pagesToPreload.push(2);
            if (totalPages > 2) pagesToPreload.push(3);
        }
        
        // Preload in background
        for (const page of pagesToPreload) {
            if (!preloadedPages.has(page)) {
                preloadedPages.add(page);
                preloadPage(page);
            }
        }
    }
    
    // Preload a specific page in background
    async function preloadPage(page) {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const productId = urlParams.get('product_id');
            let url = `/staff/inventory/search?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_dir=${sortDir}`;
            if (productId) url += `&product_id=${encodeURIComponent(productId)}`;
            if (currentBrandFilter) url += `&brand_filter=${encodeURIComponent(currentBrandFilter)}`;
            if (currentCategoryFilter) url += `&category_filter=${encodeURIComponent(currentCategoryFilter)}`;
            if (currentStockFilter) url += `&stock_filter=${encodeURIComponent(currentStockFilter)}`;
            if (currentQuery) url += `&q=${encodeURIComponent(currentQuery)}`;

            const response = await fetch(url, {
                signal: AbortSignal.timeout(5000) // 5 second timeout for preloading
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Cache the preloaded data
                    const cacheKey = url;
                    const isPaginationRequest = page !== 1;
                    const cacheToUse = isPaginationRequest ? paginationCache : cache;
                    
                    cacheToUse.set(cacheKey, {
                        data: data,
                        timestamp: Date.now()
                    });
                    
                    console.log(`🚀 Preloaded page ${page} for instant navigation`);
                }
            }
        } catch (error) {
            // Silently fail preloading - it's not critical
            console.log(`Preload failed for page ${page}:`, error.message);
        }
    }

    // Update item counter
    function updateItemCounter(pagination) {
        if (!itemRange) return;

        const totalItems = pagination.total_count || 0;
        const currentPageNum = pagination.page || currentPage;
        const startItem = totalItems === 0 ? 0 : ((currentPageNum - 1) * pageSize) + 1;
        const endItem = Math.min(currentPageNum * pageSize, totalItems);

        const itemRangeText = `Showing ${startItem}-${endItem} of ${totalItems} products`;
        itemRange.textContent = itemRangeText;
    }

    // Render inventory - optimized for instant display
    function renderInventory(products, pagination) {
        inventoryTableBody.innerHTML = '';
        mobileInventoryList.innerHTML = '';
        const screenWidth = window.innerWidth;
        const isMobile = screenWidth < 768;

        // Initialize with default values for instant display
        const orderCheckMap = {};
        products.forEach(product => {
            orderCheckMap[product.id] = {
                productId: product.id,
                hasOrders: false,
                orderCount: 0,
                preorderCount: 0
            };
        });

        // Load order status in background without blocking rendering
        Promise.all(
            products.map(async (product) => {
                try {
                    const response = await fetch(`/api/staff/products/${product.id}/has-orders`);
                    const data = await response.json();
                    return {
                        productId: product.id,
                        hasOrders: data.success ? data.has_orders : false,
                        orderCount: data.success ? data.order_count : 0,
                        preorderCount: data.success ? data.preorder_count : 0
                    };
                } catch (error) {
                    console.error(`Error checking orders for product ${product.id}:`, error);
                    return {
                        productId: product.id,
                        hasOrders: false,
                        orderCount: 0,
                        preorderCount: 0
                    };
                }
            })
        ).then(productOrderChecks => {
            // Update order status after initial render
            productOrderChecks.forEach(check => {
                orderCheckMap[check.productId] = check;
                
                // Update button visibility
                const deleteBtn = document.querySelector(`[data-id="${check.productId}"] .delete-product`);
                const archiveBtn = document.querySelector(`[data-id="${check.productId}"] .archive-product`);
                
                if (check.hasOrders) {
                    if (deleteBtn) deleteBtn.style.display = 'none';
                    if (archiveBtn) archiveBtn.style.display = 'inline-block';
                } else {
                    if (deleteBtn) deleteBtn.style.display = 'inline-block';
                    if (archiveBtn) archiveBtn.style.display = 'none';
                }
            });
        });

        products.forEach((product, index) => {
            const orderCheck = orderCheckMap[product.id];
            const hasOrders = orderCheck ? orderCheck.hasOrders : false;
            let stockClass = product.stock <= 20 ? 'low-stock' : 'sufficient-stock';
            let originalPriceDisplay = product.original_price ? `$${parseFloat(product.original_price).toFixed(2)}` : 'N/A';
            let profitMarginDisplay = 'N/A';
            if (product.original_price && product.price) {
                const originalPrice = parseFloat(product.original_price);
                const sellingPrice = parseFloat(product.price);
                const profit = sellingPrice - originalPrice;
                profitMarginDisplay = ((profit / originalPrice) * 100).toFixed(1) + '%';
            }

            // Calculate order number based on current page and position
            const orderNumber = ((currentPage - 1) * pageSize) + index + 1;

            // Table row for desktop
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${orderNumber}</td>
                <td>${product.id}</td>
                <td>${product.photo ? `<img src="/static/uploads/products/${product.photo}" class="product-image" alt="${product.name}" style="max-width: ${isMobile ? '40px' : '50px'}; max-height: ${isMobile ? '40px' : '50px'}; object-fit: cover; border-radius: 4px;">` : 'No image'}</td>
                <td>${product.name}</td>
                <td class="${isMobile ? 'd-none' : ''}">${product.description || ''}</td>
                <td>$${parseFloat(product.price).toFixed(2)}</td>
                <td class="${isMobile ? 'd-none' : ''}">${originalPriceDisplay}</td>
                <td style="display: none;">${profitMarginDisplay}</td>
                <td>
                    <div class="stock-control ${stockClass}">
                        <input type="number" class="stock-input" value="${product.stock}" min="0" data-id="${product.id}" readonly>
                    </div>
                </td>
                <td class="action-buttons ${getUserRole() === 'staff' ? 'staff-view' : ''}">
    <div class="d-flex flex-row gap-1">
        ${getUserRole() !== 'staff' ? `
            <button class="btn btn-sm btn-primary edit-product" data-id="${product.id}" 
                style="padding: ${isMobile ? '4px 8px' : '6px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'};" 
                title="Edit">
                <i class="fas fa-edit"></i>
            </button>

            <button class="btn btn-sm btn-info view-product-detail" data-id="${product.id}" 
                style="padding: ${isMobile ? '4px 8px' : '6px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'};" 
                title="View">
                <i class="fas fa-eye"></i>
            </button>

            <button class="btn btn-sm btn-danger delete-product" data-id="${product.id}" 
                style="padding: ${isMobile ? '4px 8px' : '6px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'}; ${hasOrders ? 'opacity: 0.5; cursor: not-allowed;' : ''}" 
                title="${hasOrders ? 'Cannot delete - product has orders' : 'Delete'}"
                ${hasOrders ? 'disabled' : ''}>
                <i class="fas fa-trash"></i>
            </button>

            ${product.archived ? `
                <button class="btn btn-sm btn-success restore-product" data-id="${product.id}" 
                    style="padding: ${isMobile ? '4px 8px' : '6px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'};" 
                    title="Restore">
                    <i class="fas fa-undo"></i>
                </button>
            ` : `
                <button class="btn btn-sm btn-warning archive-product" data-id="${product.id}" 
                    style="padding: ${isMobile ? '4px 8px' : '6px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'};" 
                    title="Archive">
                    <i class="fas fa-archive"></i>
                </button>
            `}
        ` : `
            <button class="btn btn-sm btn-info view-product-detail" data-id="${product.id}" 
                style="padding: ${isMobile ? '8px 16px' : '8px 12px'}; font-size: ${isMobile ? '0.8rem' : '0.9rem'};" 
                title="View Details">
                <i class="fas fa-eye"></i>
            </button>
        `}
    </div>
</td>

            `;
            inventoryTableBody.appendChild(row);

            // Mobile card
            const card = document.createElement('div');
            card.className = 'mobile-card';
            card.innerHTML = `
                <div style="display: flex; gap: 10px;">
                    ${product.photo ? `<img src="/static/uploads/products/${product.photo}" alt="${product.name}" style="max-width: ${isMobile ? '60px' : '80px'}; max-height: ${isMobile ? '60px' : '80px'}; object-fit: cover; border-radius: 4px;">` : '<div style="width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; background: #f5f5f5; border-radius: 4px;">No image</div>'}
                    <div>
                        <p><strong>Order:</strong> ${orderNumber}</p>
                        <p><strong>ID:</strong> ${product.id}</p>
                        <p><strong>Name:</strong> ${product.name}</p>
                        <p><strong>Price:</strong> $${parseFloat(product.price).toFixed(2)}</p>
                        <p><strong>Stock:</strong> <span class="${stockClass}">${product.stock}</span></p>
                        ${hasOrders ? `<p style="color: #dc3545; font-size: 0.8rem; font-weight: bold; margin: 4px 0 0 0;">⚠️ Has ${orderCheck.orderCount} orders</p>` : ''}
                    </div>
                </div>
                <div class="action-buttons ${getUserRole() === 'staff' ? 'staff-view' : ''}">
                    ${getUserRole() !== 'staff' ? `
                        <button class="btn btn-sm btn-primary edit-product" data-id="${product.id}" style="padding: 4px 8px; font-size: 0.8rem;">Edit</button>
                        <button class="btn btn-sm btn-info view-product-detail" data-id="${product.id}" style="padding: 4px 8px; font-size: 0.8rem;">View</button>
                        <button class="btn btn-sm btn-danger delete-product" data-id="${product.id}" style="padding: 4px 8px; font-size: 0.8rem; ${hasOrders ? 'opacity: 0.5; cursor: not-allowed;' : ''}" ${hasOrders ? 'disabled' : ''} title="${hasOrders ? 'Cannot delete - product has orders' : 'Delete'}">Delete</button>
                        ${product.archived ? `
                            <button class="btn btn-sm btn-success restore-product" data-id="${product.id}" style="padding: 4px 8px; font-size: 0.8rem;">Restore</button>
                        ` : `
                            <button class="btn btn-sm btn-warning archive-product" data-id="${product.id}" style="padding: 4px 8px; font-size: 0.8rem;">Archive</button>
                        `}
                    ` : `
                        <button class="btn btn-sm btn-info view-product-detail" data-id="${product.id}" style="padding: 8px 16px; font-size: 0.8rem; width: 100%;">View Details</button>
                    `}
                </div>
            `;
            mobileInventoryList.appendChild(card);
        });

        // Add event listeners
        document.querySelectorAll('.edit-product').forEach(button => {
            button.addEventListener('click', () => {
                // Redirect to edit page instead of opening modal
                window.location.href = `/staff/inventory/${button.dataset.id}/edit`;
            });
        });

        document.querySelectorAll('.view-product-detail').forEach(button => {
            button.addEventListener('click', () => openProductDetailModal(button.dataset.id));
        });

        document.querySelectorAll('.delete-product').forEach(button => {
            button.addEventListener('click', async () => {
                // Check if button is disabled
                if (button.disabled) {
                    showMessage('Cannot delete product that has orders. Consider archiving instead.', 'warning');
                    return;
                }

                const confirmed = await showDeleteConfirmation(
                    'Delete Product Permanently', 
                    'This will permanently delete the product but preserve order history. This action cannot be undone.'
                );
                
                if (!confirmed) {
                    showMessage('Product deletion cancelled.', 'info');
                    return;
                }

                try {
                    // Use denormalized deletion - preserves order history
                    const response = await fetch(`/staff/inventory/${button.dataset.id}/delete/denormalized?force=true`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();

                    if (data.success) {
                        fetchInventory();
                        showMessage('Product deleted successfully (order history preserved)!', 'success');
                    } else {
                        showMessage('Error: ' + data.error, 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showMessage('An error occurred while deleting the product.', 'error');
                }
            });
        });

        // Handle archive buttons
        document.querySelectorAll('.archive-product').forEach(button => {
            button.addEventListener('click', async () => {
                const confirmed = await showArchiveConfirmation(
                    'Archive Product', 
                    'This will move the product to archived state. You can restore it later from archived products.'
                );
                
                if (!confirmed) {
                    showMessage('Product archiving cancelled.', 'info');
                    return;
                }

                try {
                    const response = await fetch(`/staff/inventory/${button.dataset.id}/archive`, {
                        method: 'POST'
                    });
                    const data = await response.json();

                    if (data.success) {
                        fetchInventory();
                        showMessage('Product archived successfully!', 'success');
                    } else {
                        showMessage('Error: ' + data.error, 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showMessage('An error occurred while archiving the product.', 'error');
                }
            });
        });

        // Handle restore buttons
        document.querySelectorAll('.restore-product').forEach(button => {
            button.addEventListener('click', async () => {
                const productId = button.dataset.id;
                await restoreProduct(productId, 'Product');
            });
        });
    }

    // Responsive pagination
    function renderPagination(totalCount, currentPage) {
        const totalPages = Math.ceil(totalCount / pageSize);
        paginationContainer.innerHTML = '';
        if (totalPages <= 1) return;

        const isMobile = window.innerWidth < 768;
        const maxButtons = isMobile ? 3 : 5;

        const prevLi = document.createElement('li');
        prevLi.className = 'page-item' + (currentPage === 1 ? ' disabled' : '');
        prevLi.innerHTML = `<a class="page-link" href="#" aria-label="Previous" style="padding: ${isMobile ? '6px 10px' : '8px 12px'}; font-size: ${isMobile ? '0.9rem' : '1rem'};">«</a>`;
        prevLi.addEventListener('click', e => {
            e.preventDefault();
            if (currentPage > 1) {
                console.log('⚡ INSTANT: Pagination - Going to previous page');
                // Instant visual feedback
                prevLi.classList.add('active');
                setTimeout(() => prevLi.classList.remove('active'), 150);
                fetchInventory(currentPage - 1);
            }
        });
        paginationContainer.appendChild(prevLi);

        let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
        let endPage = Math.min(totalPages, startPage + maxButtons - 1);
        if (endPage === totalPages) {
            startPage = Math.max(1, totalPages - maxButtons + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const li = document.createElement('li');
            li.className = 'page-item' + (i === currentPage ? ' active' : '');
            li.innerHTML = `<a class="page-link" href="#" style="padding: ${isMobile ? '6px 10px' : '8px 12px'}; font-size: ${isMobile ? '0.9rem' : '1rem'};">${i}</a>`;
            li.addEventListener('click', e => {
                e.preventDefault();
                console.log(`⚡ INSTANT: Pagination - Going to page ${i}`);
                // Instant visual feedback
                li.classList.add('active');
                setTimeout(() => li.classList.remove('active'), 150);
                fetchInventory(i);
            });
            paginationContainer.appendChild(li);
        }

        const nextLi = document.createElement('li');
        nextLi.className = 'page-item' + (currentPage === totalPages ? ' disabled' : '');
        nextLi.innerHTML = `<a class="page-link" href="#" aria-label="Next" style="padding: ${isMobile ? '6px 10px' : '8px 12px'}; font-size: ${isMobile ? '0.9rem' : '1rem'};">»</a>`;
        nextLi.addEventListener('click', e => {
            e.preventDefault();
            if (currentPage < totalPages) {
                console.log('⚡ INSTANT: Pagination - Going to next page');
                // Instant visual feedback
                nextLi.classList.add('active');
                setTimeout(() => nextLi.classList.remove('active'), 150);
                fetchInventory(currentPage + 1);
            }
        });
        paginationContainer.appendChild(nextLi);

        if (isMobile && totalPages > endPage) {
            const loadMoreLi = document.createElement('li');
            loadMoreLi.className = 'page-item';
            loadMoreLi.innerHTML = `<a class="page-link" href="#" style="padding: 6px 10px; font-size: 0.9rem;">Load More</a>`;
            loadMoreLi.addEventListener('click', e => {
                e.preventDefault();
                console.log('⚡ INSTANT: Pagination - Load more clicked');
                // Instant visual feedback
                loadMoreLi.classList.add('active');
                setTimeout(() => loadMoreLi.classList.remove('active'), 150);
                fetchInventory(currentPage + 1);
            });
            paginationContainer.appendChild(loadMoreLi);
        }
    }

    // Edit modal function removed - Now using dedicated edit page

    // loadExistingImagesIntoEditModal function removed - Now using dedicated edit page

    // Product detail page redirect
    function openProductDetailModal(productId) {
        // Redirect to the new product details page instead of opening modal
        window.location.href = `/staff/inventory/${productId}`;
    }

    // Slideshow
    let currentSlideIndex = 0;
    let slideImages = [];

    function initializeSlideshow(product) {
        slideImages = [];
        const imageLabels = [];
        const isMobile = window.innerWidth < 768;
        const imageSize = isMobile ? '200px' : '300px';
        const thumbnailSize = isMobile ? '50px' : '60px';

        if (product.photo) {
            slideImages.push(`/static/uploads/products/${product.photo}`);
            imageLabels.push('Main Image');
        }
        if (product.back_view) {
            slideImages.push(`/static/uploads/products/${product.back_view}`);
            imageLabels.push('Back View');
        }
        if (product.left_rear_view) {
            slideImages.push(`/static/uploads/products/${product.left_rear_view}`);
            imageLabels.push('Left Rear View');
        }

        const slideshowContainer = document.getElementById('product-slideshow-container');
        const mainImage = document.getElementById('slideshow-main-image');
        const prevButton = document.querySelector('.slideshow-prev');
        const nextButton = document.querySelector('.slideshow-next');
        const counter = document.querySelector('.slideshow-counter');
        const thumbnailsContainer = document.querySelector('.slideshow-thumbnails');

        if (slideImages.length === 0) {
            slideshowContainer.style.display = 'none';
            return;
        }

        slideshowContainer.style.display = 'block';
        mainImage.style.maxHeight = imageSize;
        currentSlideIndex = 0;

        if (slideImages.length > 1) {
            prevButton.style.display = 'block';
            nextButton.style.display = 'block';
            counter.style.display = 'block';
        } else {
            prevButton.style.display = 'none';
            nextButton.style.display = 'none';
            counter.style.display = 'none';
        }

        thumbnailsContainer.innerHTML = '';
        slideImages.forEach((imageSrc, index) => {
            const thumbnail = document.createElement('div');
            thumbnail.style.cssText = `
                width: ${thumbnailSize};
                height: ${thumbnailSize};
                border: 2px solid ${index === 0 ? '#007bff' : '#dee2e6'};
                border-radius: 4px;
                overflow: hidden;
                cursor: pointer;
                background: #f8f9fa;
            `;
            const thumbImg = document.createElement('img');
            thumbImg.src = imageSrc;
            thumbImg.alt = imageLabels[index];
            thumbImg.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
            thumbImg.onclick = () => goToSlide(index);
            thumbnail.appendChild(thumbImg);
            thumbnailsContainer.appendChild(thumbnail);
        });

        updateSlideDisplay();
    }

    function updateSlideDisplay() {
        const mainImage = document.getElementById('slideshow-main-image');
        const currentSlideSpan = document.getElementById('current-slide');
        const totalSlidesSpan = document.getElementById('total-slides');
        const thumbnails = document.querySelectorAll('.slideshow-thumbnails > div');

        if (slideImages.length > 0) {
            mainImage.src = slideImages[currentSlideIndex];
            currentSlideSpan.textContent = currentSlideIndex + 1;
            totalSlidesSpan.textContent = slideImages.length;
            thumbnails.forEach((thumb, index) => {
                thumb.style.borderColor = index === currentSlideIndex ? '#007bff' : '#dee2e6';
            });
        }
    }

    window.goToSlide = function(index) {
        if (index >= 0 && index < slideImages.length) {
            currentSlideIndex = index;
            updateSlideDisplay();
        }
    };

    window.changeSlide = function(direction) {
        currentSlideIndex += direction;
        if (currentSlideIndex >= slideImages.length) {
            currentSlideIndex = 0;
        } else if (currentSlideIndex < 0) {
            currentSlideIndex = slideImages.length - 1;
        }
        updateSlideDisplay();
    };

    // Filters with debouncing to prevent rapid successive calls
    let filterTimeout;
    
    // Function to clear cache when filters change
    function clearCache() {
        cache.clear();
        paginationCache.clear();
        console.log('All caches cleared due to filter/search change');
    }
    
    window.filterProducts = function(categoryId = '', brand = '', stock = '') {
        // Clear previous timeout
        if (filterTimeout) {
            clearTimeout(filterTimeout);
        }
        
        // Debounce filter changes
        filterTimeout = setTimeout(() => {
            // Clear cache when filters change
            clearCache();
            
            currentCategoryFilter = categoryId;
            currentBrandFilter = brand;
            currentStockFilter = stock;
            currentPage = 1;
            fetchInventory();
        }, 200); // 200ms delay for filters
    };

    window.applyFilters = function() {
        const category = document.getElementById('category-filter').value;
        const brand = document.getElementById('brand-filter').value;
        const stock = document.getElementById('stock-filter').value;
        filterProducts(category, brand, stock);
    };

    // Search input functionality with debouncing to prevent lag
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        const value = searchInput.value;
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Debounce search to prevent excessive AJAX calls
        searchTimeout = setTimeout(() => {
            // Clear cache when search changes
            clearCache();
            
            if (/[a-zA-Z]/.test(value)) {
                currentQuery = value.trim();
                currentPage = 1;
                fetchInventory();
            } else if (value.trim() === '') {
                currentQuery = '';
                currentPage = 1;
                fetchInventory();
            }
        }, 300); // 300ms delay to prevent lag
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            // Clear timeout and search immediately on Enter
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            currentQuery = searchInput.value.trim();
            currentPage = 1;
            fetchInventory();
        }
    });

    // Refresh button functionality
    refreshBtn.addEventListener('click', () => {
        // Clear search input
        searchInput.value = '';
        currentQuery = '';
        
        // Reset all filters
        document.getElementById('category-filter').value = '';
        document.getElementById('brand-filter').value = '';
        document.getElementById('stock-filter').value = '';
        currentCategoryFilter = '';
        currentBrandFilter = '';
        currentStockFilter = '';
        
        // Reset pagination
        currentPage = 1;
        
        // Refresh the inventory
        fetchInventory();
        
        // Show success message
        if (window.showNotification) {
            showNotification('Search and filters cleared, inventory refreshed', 'success');
        }
    });

    // Filter dropdowns
    document.getElementById('category-filter').addEventListener('change', () => {
        searchInput.value = '';
        currentQuery = '';
        currentCategoryFilter = document.getElementById('category-filter').value;
        currentPage = 1;
        fetchInventory();
    });

    document.getElementById('brand-filter').addEventListener('change', () => {
        searchInput.value = '';
        currentQuery = '';
        currentBrandFilter = document.getElementById('brand-filter').value;
        currentPage = 1;
        fetchInventory();
    });

    document.getElementById('stock-filter').addEventListener('change', () => {
        searchInput.value = '';
        currentQuery = '';
        currentStockFilter = document.getElementById('stock-filter').value;
        currentPage = 1;
        fetchInventory();
    });

    // Responsive modal handling
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            const isMobile = window.innerWidth < 768;
            [/* addProductModal, editProductModal, */ document.getElementById('product-detail-modal')].forEach(modal => {
                if (modal.classList.contains('show-slide')) {
                    modal.querySelector('.modal-content').style.maxWidth = isMobile ? '90%' : '600px';
                    modal.querySelector('.modal-content').style.overflowY = isMobile ? 'auto' : 'visible';
                }
            });
            if (previewContainer.style.display === 'flex') updatePreviews();
            if (editPreviewContainer && editPreviewContainer.style.display === 'flex') updateEditPreviews();
        }, 100);
    });

    // Archived products are now handled through the stock filter dropdown

    // Initial load with performance monitoring
    console.log('Initializing Products Management page...');
    const startTime = performance.now();
    
    // Preload first page immediately
    fetchInventory().then(() => {
        const endTime = performance.now();
        console.log(`Initial page load took ${(endTime - startTime).toFixed(2)} milliseconds`);
    }).catch(error => {
        console.error('Initial page load failed:', error);
    });
});

async function getTotalStockForBrand(brandName) {
    try {
        const response = await fetch(`/staff/inventory/search?page_size=1000`);
        const data = await response.json();
        if (data.success && data.products) {
            let totalStock = 0;
            data.products.forEach(product => {
                if (!brandName || brandName.toLowerCase() === 'all' || product.name.toLowerCase().includes(brandName.toLowerCase())) {
                    totalStock += product.stock;
                }
            });
            return totalStock;
        } else {
            console.error('Error fetching products for brand count:', data.error);
            return null;
        }
    } catch (error) {
        console.error('Error in getTotalStockForBrand:', error);
        return null;
    }
}

// Archived products are now handled through the stock filter dropdown

// Archived products are now handled through the stock filter dropdown

// Track restore operations to prevent duplicates
const restoreInProgress = new Set();

// Restore (unarchive) a product
async function restoreProduct(productId, productName) {
    // Prevent duplicate executions
    if (restoreInProgress.has(productId)) {
        console.log('Restore already in progress for product', productId);
        return;
    }
    
    const confirmed = await showDeleteConfirmation(
        'Restore Product',
        `Are you sure you want to restore "${productName}"? This will make it visible in your regular inventory.`,
        'Restore'
    );
    
    if (!confirmed) return;
    
    // Mark restore as in progress
    restoreInProgress.add(productId);
    
    try {
        const response = await fetch(`/staff/inventory/${productId}/restore`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('Product restored successfully!', 'success');
            
            // Refresh the inventory to show the restored product
            try {
                await fetchInventory(); // Refresh current view
                
                // Update the item counter to reflect the new total
                const itemCounterElement = document.querySelector('.item-counter');
                if (itemCounterElement) {
                    itemCounterElement.style.display = 'block';
                }
            } catch (refreshError) {
                console.error('Error refreshing inventory:', refreshError);
                // Even if refresh fails, show success message
                showMessage('Product restored successfully! Please refresh the page to see changes.', 'success');
            }
        } else {
            showMessage('Error: ' + (data.error || 'Unknown error occurred'), 'error');
        }
    } catch (error) {
        console.error('Error restoring product:', error);
        showMessage('An error occurred while restoring the product.', 'error');
    } finally {
        // Remove from in-progress set after a delay to prevent rapid re-clicks
        setTimeout(() => {
            restoreInProgress.delete(productId);
        }, 1000);
    }
}

// Professional delete confirmation modal
function showDeleteConfirmation(title, message, actionButtonText = 'Delete') {
    return new Promise((resolve) => {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.className = 'delete-confirmation-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(2px);
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'delete-confirmation-modal';
        modal.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 0;
            max-width: 420px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            transform: scale(0.9);
            transition: transform 0.2s ease;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        modal.innerHTML = `
            <div style="padding: 24px 24px 16px 24px; text-align: center;">
                <div style="width: 64px; height: 64px; background: #fee2e2; border-radius: 50%; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center;">
                    <svg width="32" height="32" fill="#dc2626" viewBox="0 0 24 24">
                        <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
                    </svg>
                </div>
                <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #111827;">${title}</h3>
                <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">${message}</p>
            </div>
            <div style="padding: 16px 24px 24px 24px; display: flex; gap: 12px; justify-content: center;">
                <button class="cancel-btn" style="
                    background: #f3f4f6;
                    color: #374151;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 500;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background-color 0.2s;
                    min-width: 80px;
                ">Cancel</button>
                <button class="delete-btn" style="
                    background: #dc2626;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 500;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background-color 0.2s;
                    min-width: 80px;
                ">${actionButtonText}</button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Animate in
        requestAnimationFrame(() => {
            modal.style.transform = 'scale(1)';
        });

        // Add hover effects
        const cancelBtn = modal.querySelector('.cancel-btn');
        const deleteBtn = modal.querySelector('.delete-btn');

        cancelBtn.addEventListener('mouseenter', () => {
            cancelBtn.style.backgroundColor = '#e5e7eb';
        });
        cancelBtn.addEventListener('mouseleave', () => {
            cancelBtn.style.backgroundColor = '#f3f4f6';
        });

        deleteBtn.addEventListener('mouseenter', () => {
            deleteBtn.style.backgroundColor = '#b91c1c';
        });
        deleteBtn.addEventListener('mouseleave', () => {
            deleteBtn.style.backgroundColor = '#dc2626';
        });

        // Handle button clicks
        const cleanup = () => {
            modal.style.transform = 'scale(0.9)';
            overlay.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(overlay);
            }, 200);
        };

        cancelBtn.addEventListener('click', () => {
            cleanup();
            resolve(false);
        });

        deleteBtn.addEventListener('click', () => {
            cleanup();
            resolve(true);
        });

        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                cleanup();
                resolve(false);
            }
        });

        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                resolve(false);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    });
}

// Archive confirmation modal (similar to delete but with "Archive" button)
function showArchiveConfirmation(title, message) {
    return new Promise((resolve) => {
        // Create modal HTML
        const modalHTML = `
            <div class="archive-modal-overlay" id="archiveModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            ">
                <div class="archive-modal-content" style="
                    background: white;
                    border-radius: 8px;
                    padding: 24px;
                    max-width: 400px;
                    width: 90%;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                ">
                    <div class="archive-modal-header" style="
                        margin-bottom: 16px;
                        text-align: center;
                    ">
                        <div style="
                            width: 60px;
                            height: 60px;
                            background: #fff3cd;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin: 0 auto 16px auto;
                        ">
                            <span style="
                                font-size: 24px;
                                color: #856404;
                            ">📁</span>
                        </div>
                        <h3 style="
                            margin: 0;
                            color: #856404;
                            font-size: 18px;
                            font-weight: 600;
                        ">${title}</h3>
                    </div>
                    <div class="archive-modal-body" style="
                        margin-bottom: 24px;
                        color: #333;
                        line-height: 1.5;
                        text-align: center;
                    ">
                        ${message}
                    </div>
                    <div class="archive-modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 12px;
                    ">
                        <button class="cancel-archive-btn" style="
                            padding: 10px 20px;
                            border: 1px solid #ddd;
                            background: white;
                            color: #666;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                        ">Cancel</button>
                        <button class="confirm-archive-btn" style="
                            padding: 10px 20px;
                            border: none;
                            background: #ffc107;
                            color: #212529;
                            border-radius: 4px;
                            cursor: pointer;
                            font-weight: 500;
                            font-size: 14px;
                        ">Archive</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        const modal = document.getElementById('archiveModal');
        const cancelBtn = modal.querySelector('.cancel-archive-btn');
        const confirmBtn = modal.querySelector('.confirm-archive-btn');

        // Event handlers
        const cleanup = () => {
            modal.remove();
        };

        cancelBtn.addEventListener('click', () => {
            cleanup();
            resolve(false);
        });

        confirmBtn.addEventListener('click', () => {
            cleanup();
            resolve(true);
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                cleanup();
                resolve(false);
            }
        });

        // Close on escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                document.removeEventListener('keydown', handleEscape);
                resolve(false);
            }
        };
        document.addEventListener('keydown', handleEscape);
    });
}
