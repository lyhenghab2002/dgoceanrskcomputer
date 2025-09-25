// Date Range Widget JavaScript - Day Selection Version
class DateRangeWidget {
    constructor() {
        this.startDate = null;
        this.endDate = null;
        this.minDate = null;
        this.maxDate = null;
        this.selectedDays = new Set();
        this.filteredData = null;
        this.debounceTimer = null;
        this.isUpdating = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeDates();
        this.setupDaySelection();
        this.loadInitialData();
        
        console.log('Date Range Widget (Day Selection) initialized');
    }
    
    setupEventListeners() {
        // Date input listeners
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        
        if (startDateInput) {
            startDateInput.addEventListener('change', (e) => {
                this.startDate = new Date(e.target.value);
                this.updateDayList();
                this.loadFilteredData();
            });
        } else {
            console.warn('Start date input not found');
        }
        
        if (endDateInput) {
            endDateInput.addEventListener('change', (e) => {
                this.endDate = new Date(e.target.value);
                this.updateDayList();
                this.loadFilteredData();
            });
        } else {
            console.warn('End date input not found');
        }
        
        // Export button listeners
        const exportPDFBtn = document.getElementById('exportDateRangePDF');
        if (exportPDFBtn) {
            exportPDFBtn.addEventListener('click', () => {
                this.exportToPDF();
            });
        }
        
        const exportCSVBtn = document.getElementById('exportDateRangeCSV');
        if (exportCSVBtn) {
            exportCSVBtn.addEventListener('click', () => {
                this.exportToCSV();
            });
        }
        
        // No additional event listeners needed for the simple list view
    }
    
    initializeDates() {
        // Set default date range to last 30 days
        const today = new Date();
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(today.getDate() - 30);
        
        this.endDate = today;
        this.startDate = thirtyDaysAgo;
        
        // Set min/max dates (last 2 years)
        this.minDate = new Date(today);
        this.minDate.setFullYear(today.getFullYear() - 2);
        this.maxDate = today;
        
        // Update input fields
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        
        if (startDateInput) {
            startDateInput.value = this.formatDate(this.startDate);
            startDateInput.max = this.formatDate(this.maxDate);
            startDateInput.min = this.formatDate(this.minDate);
        }
        
        if (endDateInput) {
            endDateInput.value = this.formatDate(this.endDate);
            endDateInput.max = this.formatDate(this.maxDate);
            endDateInput.min = this.formatDate(this.minDate);
        }
    }
    
    setupDaySelection() {
        this.updateDayList();
    }
    
    updateDayList() {
        const dayList = document.getElementById('dayList');
        if (!dayList) {
            console.warn('Day list container not found');
            return;
        }
        
        // Clear existing days
        dayList.innerHTML = '';
        
        if (!this.startDate || !this.endDate) {
            return;
        }
        
        // Generate days between start and end date
        const days = this.getDaysBetweenDates(this.startDate, this.endDate);
        
        days.forEach(day => {
            const dayElement = this.createDayElement(day);
            dayList.appendChild(dayElement);
        });
    }
    
    getDaysBetweenDates(startDate, endDate) {
        const days = [];
        const currentDate = new Date(startDate);
        
        while (currentDate <= endDate) {
            days.push(new Date(currentDate));
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        return days;
    }
    
    createDayElement(date) {
        const dayElement = document.createElement('tr');
        dayElement.className = 'day-item';
        dayElement.dataset.date = this.formatDate(date);
        
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNumber = date.getDate();
        const monthName = date.toLocaleDateString('en-US', { month: 'short' });
        const fullDate = date.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        dayElement.innerHTML = `
            <td class="day-column">
                <div class="day-number">${dayNumber}</div>
                <div class="day-name">${dayName}</div>
            </td>
            <td class="date-column">
                <div class="full-date">${fullDate}</div>
            </td>
            <td class="revenue-column">
                <div class="revenue-amount" data-date="${this.formatDate(date)}">Loading...</div>
            </td>
            <td class="orders-column">
                <div class="orders-count" data-date="${this.formatDate(date)}">Loading...</div>
            </td>
            <td class="actions-column">
                <div class="action-buttons">
                    <button class="view-button" onclick="viewDayDetails('${this.formatDate(date)}', '${fullDate}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="export-button" onclick="exportDayData('${this.formatDate(date)}', '${fullDate}')">
                        <i class="fas fa-file-export"></i> Export
                    </button>
                </div>
            </td>
        `;
        
        // Load revenue data for this day
        this.loadDayRevenue(date, dayElement);
        
        return dayElement;
    }
    
    async loadDayRevenue(date, dayElement) {
        try {
            const response = await fetch(`/api/revenue/daily?date=${this.formatDate(date)}`);
            const data = await response.json();
            
            const revenueElement = dayElement.querySelector('.revenue-amount');
            const ordersElement = dayElement.querySelector('.orders-count');
            
            if (revenueElement) {
                if (data.success && data.revenue !== undefined) {
                    revenueElement.textContent = `$${data.revenue.toFixed(2)}`;
                } else {
                    revenueElement.textContent = '$0.00';
                }
            }
            
            if (ordersElement) {
                if (data.success && data.orders !== undefined) {
                    ordersElement.textContent = data.orders;
                } else {
                    ordersElement.textContent = '0';
                }
            }
        } catch (error) {
            console.error('Error loading day revenue:', error);
            const revenueElement = dayElement.querySelector('.revenue-amount');
            const ordersElement = dayElement.querySelector('.orders-count');
            
            if (revenueElement) {
                revenueElement.textContent = '$0.00';
            }
            if (ordersElement) {
                ordersElement.textContent = '0';
            }
        }
    }
    
    
    async loadFilteredData() {
        if (this.isUpdating) return;
        
        this.isUpdating = true;
        
        try {
            // If no days selected, show all data in range
            if (this.selectedDays.size === 0) {
                await this.loadDateRangeData();
            } else {
                await this.loadSelectedDaysData();
            }
        } catch (error) {
            console.error('Error loading filtered data:', error);
        } finally {
            this.isUpdating = false;
        }
    }
    
    async loadDateRangeData() {
        const startDate = this.formatDate(this.startDate);
        const endDate = this.formatDate(this.endDate);
        
        try {
            const response = await fetch(`/api/revenue/range?start_date=${startDate}&end_date=${endDate}`);
            const data = await response.json();
            
            if (data.success) {
                this.filteredData = data.data;
                this.updateRevenueWidgets();
            }
        } catch (error) {
            console.error('Error loading date range data:', error);
        }
    }
    
    async loadSelectedDaysData() {
        const selectedDates = Array.from(this.selectedDays);
        
        try {
            const response = await fetch('/api/revenue/selected-days', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ dates: selectedDates })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.filteredData = data.data;
                this.updateRevenueWidgets();
            }
        } catch (error) {
            console.error('Error loading selected days data:', error);
        }
    }
    
    async loadInitialData() {
        await this.loadFilteredData();
    }
    
    updateRevenueWidgets() {
        // Update monthly revenue widget
        if (window.updateMonthlyRevenueWidget) {
            window.updateMonthlyRevenueWidget(this.filteredData);
        }
        
        // Update yearly revenue widget
        if (window.updateYearlyRevenueWidget) {
            window.updateYearlyRevenueWidget(this.filteredData);
        }
        
        // Update top selling products widget
        if (window.updateTopSellingProductsWidget) {
            window.updateTopSellingProductsWidget(this.filteredData);
        }
    }
    
    formatDate(date) {
        if (!date) return '';
        return date.toISOString().split('T')[0];
    }
    
    async exportToPDF() {
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Add title
            doc.setFontSize(20);
            doc.text('Date Range Report', 20, 20);
            
            // Add date range
            doc.setFontSize(12);
            const startDateStr = this.formatDate(this.startDate);
            const endDateStr = this.formatDate(this.endDate);
            doc.text(`Date Range: ${startDateStr} to ${endDateStr}`, 20, 35);
            
            // Add selected days info
            if (this.selectedDays.size > 0) {
                doc.text(`Selected Days: ${this.selectedDays.size} days`, 20, 45);
            }
            
            // Add data table
            if (this.filteredData && this.filteredData.length > 0) {
                const tableData = this.filteredData.map(item => [
                    item.date || '-',
                    item.orders || 0,
                    `$${(item.revenue || 0).toFixed(2)}`,
                    item.trend || '-'
                ]);
                
                doc.autoTable({
                    head: [['Date', 'Orders', 'Revenue', 'Trend']],
                    body: tableData,
                    startY: 60,
                    styles: { fontSize: 10 }
                });
            }
            
            // Save the PDF
            const fileName = `date_range_report_${startDateStr}_to_${endDateStr}.pdf`;
            doc.save(fileName);
            
        } catch (error) {
            console.error('Error exporting to PDF:', error);
            alert('Error exporting to PDF. Please try again.');
        }
    }
    
    async exportToCSV() {
        try {
            if (!this.filteredData || this.filteredData.length === 0) {
                alert('No data to export');
                return;
            }
            
            // Create CSV content
            const headers = ['Date', 'Orders', 'Revenue', 'Trend'];
            const csvContent = [
                headers.join(','),
                ...this.filteredData.map(item => [
                    item.date || '',
                    item.orders || 0,
                    item.revenue || 0,
                    item.trend || ''
                ].join(','))
            ].join('\n');
            
            // Create and download file
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const startDateStr = this.formatDate(this.startDate);
            const endDateStr = this.formatDate(this.endDate);
            a.download = `date_range_report_${startDateStr}_to_${endDateStr}.csv`;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Error exporting to CSV:', error);
            alert('Error exporting to CSV. Please try again.');
        }
    }
}

// Make viewDayDetails globally accessible
window.viewDayDetails = function(dateString, fullDate) {
    console.log('🔍 DEBUG: viewDayDetails called');
    console.log(`🔍 DEBUG: Viewing details for ${fullDate} (${dateString})`);
    
    // Check if Bootstrap is available
    console.log('🔍 DEBUG: Bootstrap available:', typeof bootstrap !== 'undefined');
    console.log('🔍 DEBUG: Bootstrap Modal available:', typeof bootstrap?.Modal !== 'undefined');
    
    // Check if modal element exists
    const modalElement = document.getElementById('dayDetailModal');
    console.log('🔍 DEBUG: Modal element found:', modalElement);
    
    if (!modalElement) {
        console.error('❌ ERROR: dayDetailModal element not found!');
        alert('Modal element not found! Check console for details.');
        return;
    }
    
    // Check if modal content exists
    const modalContent = document.querySelector('.day-details-content');
    console.log('🔍 DEBUG: Modal content found:', modalContent);
    
    if (!modalContent) {
        console.error('❌ ERROR: .day-details-content not found!');
        alert('Modal content not found! Check console for details.');
        return;
    }
    
    // Show loading state
    console.log('🔍 DEBUG: Creating Bootstrap modal instance');
    const modal = new bootstrap.Modal(modalElement);
    
    // Show immediate test content to verify modal is working
    console.log('🔍 DEBUG: Setting initial modal content');
    modalContent.innerHTML = `
        <div class="day-details-header">
            <h3>${fullDate}</h3>
            <div class="day-date">${dateString}</div>
        </div>
        
        <div class="alert alert-success">
            <h4>✅ Modal is Working!</h4>
            <p><strong>Date:</strong> ${dateString}</p>
            <p><strong>Full Date:</strong> ${fullDate}</p>
            <p><strong>Time:</strong> ${new Date().toLocaleTimeString()}</p>
            <button class="btn btn-primary" onclick="testAPI('${dateString}')">Test API Call</button>
        </div>
    `;
    
    console.log('🔍 DEBUG: Modal content set, showing modal');
    modal.show();
    
    console.log('🔍 DEBUG: Modal shown, setting timeout for loadDayDetails');
    // Wait a moment for the modal to be fully displayed, then load data
    setTimeout(() => {
        console.log('🔍 DEBUG: Timeout reached, calling loadDayDetails');
        loadDayDetails(dateString, fullDate);
    }, 100);
};

// Test function to manually test the API
window.testAPI = function(dateString) {
    console.log('Testing API for date:', dateString);
    fetch(`/api/revenue/daily-details?date=${dateString}`)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('API Response:', data);
            alert('API Response: ' + JSON.stringify(data, null, 2));
        })
        .catch(error => {
            console.error('API Error:', error);
            alert('API Error: ' + error.message);
        });
};

// Function to load detailed day data
async function loadDayDetails(dateString, fullDate) {
    console.log('🔍 DEBUG: Starting loadDayDetails function');
    console.log('🔍 DEBUG: dateString =', dateString);
    console.log('🔍 DEBUG: fullDate =', fullDate);
    
    try {
        console.log(`🔍 DEBUG: Loading details for ${dateString}`);
        
        // Check if modal exists
        const modal = document.getElementById('dayDetailModal');
        console.log('🔍 DEBUG: Modal element found:', modal);
        
        if (!modal) {
            console.error('❌ ERROR: dayDetailModal not found in DOM');
            alert('Modal not found! Check console for details.');
            return;
        }
        
        // Check if modal content exists
        const modalContent = document.querySelector('.day-details-content');
        console.log('🔍 DEBUG: Modal content element found:', modalContent);
        console.log('🔍 DEBUG: Modal content element type:', typeof modalContent);
        console.log('🔍 DEBUG: Modal content element classList:', modalContent ? modalContent.classList : 'null');
        
        if (!modalContent) {
            console.error('❌ ERROR: .day-details-content not found in DOM');
            console.log('🔍 DEBUG: Available elements with "day" in class name:');
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                if (el.className && el.className.includes('day')) {
                    console.log('  - Element:', el, 'Classes:', el.className);
                }
            });
            alert('Modal content not found! Check console for details.');
            return;
        }
        
        // First, let's test with a simple API call to see if the endpoint works
        console.log('🔍 DEBUG: Making API call to /api/revenue/daily-details?date=' + dateString);
        const response = await fetch(`/api/revenue/daily-details?date=${dateString}`);
        console.log('🔍 DEBUG: Response status:', response.status);
        console.log('🔍 DEBUG: Response ok:', response.ok);
        console.log('🔍 DEBUG: Response headers:', response.headers);
        
        if (!response.ok) {
            console.error('❌ ERROR: API response not ok:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('❌ ERROR: Response body:', errorText);
            alert(`API Error: ${response.status} - ${response.statusText}`);
            return;
        }
        
        const data = await response.json();
        console.log('🔍 DEBUG: API Response data:', data);
        console.log('🔍 DEBUG: API Response success:', data.success);
        console.log('🔍 DEBUG: API Response type:', typeof data);
        console.log('🔍 DEBUG: API Response keys:', Object.keys(data));
        
        // Build complete modal content
        console.log('🔍 DEBUG: Building modal HTML content');
        let completeHtml = `
            <div class="day-details-header">
                <h3>${fullDate}</h3>
                <div class="day-date">${dateString}</div>
            </div>
        `;
        
        console.log('🔍 DEBUG: Header HTML built:', completeHtml);
        
        // If we have data, add it to the complete HTML
        if (data.success) {
            console.log('🔍 DEBUG: Data is successful, building stats HTML');
            console.log('🔍 DEBUG: total_revenue =', data.total_revenue);
            console.log('🔍 DEBUG: total_orders =', data.total_orders);
            console.log('🔍 DEBUG: avg_order_value =', data.avg_order_value);
            console.log('🔍 DEBUG: total_products =', data.total_products);
            console.log('🔍 DEBUG: orders array =', data.orders);
            console.log('🔍 DEBUG: orders length =', data.orders ? data.orders.length : 'null');
            
            const statsHtml = `
                <div class="day-details-stats">
                    <div class="day-stat-card">
                        <div class="stat-icon revenue">
                            <i class="fas fa-dollar-sign"></i>
                        </div>
                        <div class="stat-value">$${data.total_revenue ? data.total_revenue.toFixed(2) : '0.00'}</div>
                        <div class="stat-label">Total Revenue</div>
                    </div>
                    
                    <div class="day-stat-card">
                        <div class="stat-icon orders">
                            <i class="fas fa-shopping-cart"></i>
                        </div>
                        <div class="stat-value">${data.total_orders || 0}</div>
                        <div class="stat-label">Total Orders</div>
                    </div>
                    
                    <div class="day-stat-card">
                        <div class="stat-icon avg-order">
                            <i class="fas fa-chart-line"></i>
                        </div>
                        <div class="stat-value">$${data.avg_order_value ? data.avg_order_value.toFixed(2) : '0.00'}</div>
                        <div class="stat-label">Avg Order Value</div>
                    </div>
                    
                    <div class="day-stat-card">
                        <div class="stat-icon products">
                            <i class="fas fa-box"></i>
                        </div>
                        <div class="stat-value">${data.total_products || 0}</div>
                        <div class="stat-label">Products Sold</div>
                    </div>
                </div>
                
                <div class="day-orders-table">
                    <h5><i class="fas fa-list"></i> Orders for ${fullDate}</h5>
                    ${data.orders && data.orders.length > 0 ? `
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Order ID</th>
                                        <th>Customer</th>
                                        <th>Time</th>
                                        <th>Items</th>
                                        <th>Total</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.orders.map(order => `
                                        <tr>
                                            <td><strong>#${order.id}</strong></td>
                                            <td>${order.customer_name || 'N/A'}</td>
                                            <td>${order.time || 'N/A'}</td>
                                            <td>${order.items_count || 0}</td>
                                            <td><strong>$${order.total ? order.total.toFixed(2) : '0.00'}</strong></td>
                                            <td><span class="badge bg-${order.status === 'completed' ? 'success' : 'warning'}">${order.status || 'N/A'}</span></td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : `
                        <div class="no-orders-message">
                            <i class="fas fa-shopping-cart"></i>
                            <p>No orders found for this day</p>
                            <small class="text-muted">This could mean there are no orders, or the orders don't meet the status criteria.</small>
                        </div>
                    `}
                </div>
            `;
            
            completeHtml += statsHtml;
            console.log('🔍 DEBUG: Stats HTML added, complete HTML length:', completeHtml.length);
        } else {
            console.log('🔍 DEBUG: Data is not successful, adding error message');
            completeHtml += `
                <div class="no-orders-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading day details: ${data.error || 'Unknown error'}</p>
                </div>
            `;
        }
        
        console.log('🔍 DEBUG: About to set modal content');
        console.log('🔍 DEBUG: Modal content element before update:', modalContent);
        console.log('🔍 DEBUG: Modal content innerHTML before update:', modalContent.innerHTML);
        
        // Set the complete HTML content at once
        modalContent.innerHTML = completeHtml;
        
        console.log('🔍 DEBUG: Modal content set successfully');
        console.log('🔍 DEBUG: Modal content innerHTML after update:', modalContent.innerHTML);
        console.log('🔍 DEBUG: Modal content children count:', modalContent.children.length);
        console.log('🔍 DEBUG: Modal content first child:', modalContent.firstChild);
        
        // Verify the content is actually visible
        setTimeout(() => {
            console.log('🔍 DEBUG: After 1 second - Modal content innerHTML:', modalContent.innerHTML);
            console.log('🔍 DEBUG: After 1 second - Modal content children:', modalContent.children);
            console.log('🔍 DEBUG: After 1 second - Modal visible:', modal.style.display !== 'none');
            console.log('🔍 DEBUG: After 1 second - Modal classList:', modal.classList);
        }, 1000);
    } catch (error) {
        console.error('Error loading day details:', error);
        const modalContent = document.querySelector('.day-details-content');
        modalContent.innerHTML = `
            <div class="day-details-header">
                <h3>${fullDate}</h3>
                <div class="day-date">${dateString}</div>
            </div>
            <div class="alert alert-danger">
                <strong>JavaScript Error:</strong> ${error.message}<br>
                <strong>Stack:</strong> ${error.stack}
            </div>
        `;
    }
}

// Make exportDayData globally accessible
window.exportDayData = function(dateString, fullDate) {
    // Export data for a specific day
    console.log(`Exporting data for ${fullDate} (${dateString})`);
    
    // Call the API to get the day data and export it
    exportDayDataToPDF(dateString, fullDate);
};

// Function to export day data to PDF
async function exportDayDataToPDF(dateString, fullDate) {
    try {
        console.log(`🔍 DEBUG: Starting PDF export for ${fullDate} (${dateString})`);
        
        // Check if jsPDF is available
        console.log('🔍 DEBUG: Checking jsPDF availability...');
        console.log('🔍 DEBUG: window.jspdf:', typeof window.jspdf);
        console.log('🔍 DEBUG: window.jspdf:', window.jspdf);
        
        if (!window.jspdf) {
            throw new Error('jsPDF library not loaded. Please refresh the page and try again.');
        }
        
        const { jsPDF } = window.jspdf;
        console.log('🔍 DEBUG: jsPDF constructor:', typeof jsPDF);
        
        if (typeof jsPDF !== 'function') {
            throw new Error('jsPDF constructor not available. Library may not be loaded properly.');
        }
        
        // Show loading state
        const exportBtn = document.getElementById('exportDayDetails');
        if (exportBtn) {
            const originalText = exportBtn.innerHTML;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
            exportBtn.disabled = true;
        }
        
        console.log('🔍 DEBUG: Fetching day data from API...');
        // Get the day data
        const response = await fetch(`/api/revenue/daily-details?date=${dateString}`);
        console.log('🔍 DEBUG: API response status:', response.status);
        
        const data = await response.json();
        console.log('🔍 DEBUG: API response data:', data);
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch day data');
        }
        
        console.log('🔍 DEBUG: Creating PDF document...');
        // Create PDF using jsPDF
        const doc = new jsPDF();
        console.log('🔍 DEBUG: PDF document created:', doc);
        
        console.log('🔍 DEBUG: Adding content to PDF...');
        // Add title
        doc.setFontSize(20);
        doc.text('Day Details Report', 20, 20);
        
        // Add date
        doc.setFontSize(14);
        doc.text(`Date: ${fullDate}`, 20, 35);
        doc.text(`Report Date: ${dateString}`, 20, 45);
        
        // Add summary statistics
        doc.setFontSize(12);
        doc.text('Summary Statistics', 20, 65);
        
        const stats = [
            `Total Revenue: $${data.total_revenue ? data.total_revenue.toFixed(2) : '0.00'}`,
            `Total Orders: ${data.total_orders || 0}`,
            `Average Order Value: $${data.avg_order_value ? data.avg_order_value.toFixed(2) : '0.00'}`,
            `Products Sold: ${data.total_products || 0}`
        ];
        
        console.log('🔍 DEBUG: Adding stats to PDF:', stats);
        stats.forEach((stat, index) => {
            doc.text(stat, 30, 80 + (index * 10));
        });
        
        // Add orders table if there are orders
        if (data.orders && data.orders.length > 0) {
            console.log('🔍 DEBUG: Adding orders table to PDF...');
            doc.text('Orders Details', 20, 130);
            
            const tableData = data.orders.map(order => [
                `#${order.id}`,
                order.customer_name || 'N/A',
                order.time || 'N/A',
                order.items_count || 0,
                `$${order.total ? order.total.toFixed(2) : '0.00'}`,
                order.status || 'N/A'
            ]);
            
            console.log('🔍 DEBUG: Table data:', tableData);
            
            // Check if autoTable is available
            if (typeof doc.autoTable === 'function') {
                console.log('🔍 DEBUG: autoTable function available, creating table...');
                doc.autoTable({
                    head: [['Order ID', 'Customer', 'Time', 'Items', 'Total', 'Status']],
                    body: tableData,
                    startY: 140,
                    styles: { fontSize: 8 },
                    headStyles: { fillColor: [52, 152, 219] }
                });
                console.log('🔍 DEBUG: Table created successfully');
            } else {
                console.log('🔍 DEBUG: autoTable not available, adding simple table...');
                // Fallback: add table data as text
                tableData.forEach((row, index) => {
                    doc.text(row.join(' | '), 20, 150 + (index * 10));
                });
            }
        } else {
            console.log('🔍 DEBUG: No orders found, adding message...');
            doc.text('No orders found for this day', 20, 130);
        }
        
        console.log('🔍 DEBUG: Adding footer to PDF...');
        // Add footer
        const pageCount = doc.internal.getNumberOfPages();
        for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i);
            doc.setFontSize(8);
            doc.text(`Page ${i} of ${pageCount}`, 20, doc.internal.pageSize.height - 10);
            doc.text(`Generated on ${new Date().toLocaleString()}`, doc.internal.pageSize.width - 80, doc.internal.pageSize.height - 10);
        }
        
        console.log('🔍 DEBUG: Saving PDF...');
        // Save the PDF
        const fileName = `day_details_${dateString.replace(/-/g, '_')}.pdf`;
        console.log('🔍 DEBUG: File name:', fileName);
        
        doc.save(fileName);
        console.log(`✅ PDF exported successfully: ${fileName}`);
        
        // Reset button
        if (exportBtn) {
            exportBtn.innerHTML = '<i class="fas fa-file-export"></i> Export Day Data';
            exportBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('❌ Error exporting day data:', error);
        console.error('❌ Error details:', error.stack);
        
        // Try fallback CSV export if PDF fails
        console.log('🔍 DEBUG: Attempting fallback CSV export...');
        try {
            await exportDayDataToCSV(dateString, fullDate);
        } catch (csvError) {
            console.error('❌ CSV export also failed:', csvError);
            alert(`Error exporting data: ${error.message}\n\nTried PDF and CSV export, both failed.`);
        }
        
        // Reset button
        const exportBtn = document.getElementById('exportDayDetails');
        if (exportBtn) {
            exportBtn.innerHTML = '<i class="fas fa-file-export"></i> Export Day Data';
            exportBtn.disabled = false;
        }
    }
}

// Fallback CSV export function
async function exportDayDataToCSV(dateString, fullDate) {
    try {
        console.log(`🔍 DEBUG: Starting CSV export for ${fullDate} (${dateString})`);
        
        // Get the day data
        const response = await fetch(`/api/revenue/daily-details?date=${dateString}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch day data');
        }
        
        // Create CSV content
        let csvContent = `Day Details Report\n`;
        csvContent += `Date: ${fullDate}\n`;
        csvContent += `Report Date: ${dateString}\n\n`;
        csvContent += `Summary Statistics\n`;
        csvContent += `Total Revenue,${data.total_revenue ? data.total_revenue.toFixed(2) : '0.00'}\n`;
        csvContent += `Total Orders,${data.total_orders || 0}\n`;
        csvContent += `Average Order Value,${data.avg_order_value ? data.avg_order_value.toFixed(2) : '0.00'}\n`;
        csvContent += `Products Sold,${data.total_products || 0}\n\n`;
        
        if (data.orders && data.orders.length > 0) {
            csvContent += `Orders Details\n`;
            csvContent += `Order ID,Customer,Time,Items,Total,Status\n`;
            data.orders.forEach(order => {
                csvContent += `#${order.id},"${order.customer_name || 'N/A'}",${order.time || 'N/A'},${order.items_count || 0},${order.total ? order.total.toFixed(2) : '0.00'},${order.status || 'N/A'}\n`;
            });
        } else {
            csvContent += `No orders found for this day\n`;
        }
        
        // Create and download CSV file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `day_details_${dateString.replace(/-/g, '_')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log(`✅ CSV exported successfully: day_details_${dateString.replace(/-/g, '_')}.csv`);
        
    } catch (error) {
        console.error('❌ CSV export failed:', error);
        throw error;
    }
}

// Initialize the widget when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DateRangeWidget();
    
    // Add event listener for the export button in the modal footer
    const exportBtn = document.getElementById('exportDayDetails');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // Get the current date from the modal header
            const modal = document.getElementById('dayDetailModal');
            const modalTitle = modal.querySelector('.modal-title');
            const dateElement = modal.querySelector('.day-date');
            
            if (dateElement) {
                const dateString = dateElement.textContent.trim();
                const fullDate = modalTitle ? modalTitle.textContent.replace('Day Details', '').trim() : dateString;
                
                console.log('Export button clicked in modal footer');
                exportDayDataToPDF(dateString, fullDate);
            } else {
                console.error('Could not find date information in modal');
                alert('Could not find date information. Please try again.');
            }
        });
    } else {
        console.warn('Export button not found with ID: exportDayDetails');
    }
});