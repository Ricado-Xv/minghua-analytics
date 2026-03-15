// Store original content for each report
var originalContent = {};

function showReport(type, monthIdx, index) {
    var targetId = type + '-' + monthIdx + '-' + index;
    
    // Hide all contents of this type and month
    document.querySelectorAll('.report-content').forEach(function(c) {
        if (c.id.startsWith(type + '-' + monthIdx + '-')) {
            c.classList.remove('active');
        }
    });
    
    // Show selected
    var targetEl = document.getElementById(targetId);
    if (targetEl) {
        targetEl.classList.add('active');
        
        // Save original content if not saved
        if (!originalContent[targetId]) {
            originalContent[targetId] = targetEl.innerHTML;
        }
        
        // Apply current store type filter
        var filterSelect = document.getElementById('store-type-' + monthIdx + '-select');
        if (filterSelect) {
            filterStoreType(type, monthIdx, filterSelect.value);
        }
    }
}

// Global filter for all report types in a month
function filterAllStoreTypes(monthIdx, filterType) {
    filterStoreType('week', monthIdx, filterType);
    filterStoreType('cross', monthIdx, filterType);
    filterStoreType('monthly', monthIdx, filterType);
    filterStoreType('global', monthIdx, filterType);
}

function filterStoreType(type, monthIdx, filterType) {
    var contentId;
    if (type === 'global') {
        contentId = 'global-cross-0';
    } else {
        contentId = type + '-' + monthIdx + '-0';
    }
    var contentEl = document.getElementById(contentId);
    if (!contentEl) return;
    
    // Get original content
    var orig = originalContent[contentId];
    if (!orig) {
        orig = contentEl.innerHTML;
        originalContent[contentId] = orig;
    }
    
    // Get text content from original
    var tempDiv = document.createElement('div');
    tempDiv.innerHTML = orig;
    
    // Find header and get text after it
    var headerEl = tempDiv.querySelector('.report-header');
    var textContent = '';
    if (headerEl) {
        var current = headerEl.nextSibling;
        while (current) {
            if (current.nodeType === Node.TEXT_NODE) {
                textContent += current.textContent;
            }
            current = current.nextSibling;
        }
    }
    
    if (!textContent) {
        textContent = tempDiv.textContent || tempDiv.innerText;
    }
    
    var lines = textContent.split('\n');
    var filteredLines = [];
    var showAll = (filterType === 'all');
    
    // All section headers to look for
    var sectionHeaders = [
        '【每周整体情况】',
        '【环比变化】',
        '【整体趋势】',
        '【平均周量】',
        '【日均进货金额对比】',
        '【水果种类变化】',
        '【水果金额环比变化】',
        '【店铺金额环比变化】',
        '【店铺对比】',
        '【按店铺汇总】',
        '【各店进货情况】'
    ];
    
    var inSection = false;
    var sectionName = '';
    
    lines.forEach(function(line) {
        // Check if we entered a relevant section
        var enteredSection = false;
        for (var i = 0; i < sectionHeaders.length; i++) {
            if (line.includes(sectionHeaders[i])) {
                inSection = true;
                enteredSection = true;
                sectionName = sectionHeaders[i];
                break;
            }
        }
        
        if (enteredSection) {
            filteredLines.push(line);
            return;
        }
        
        // Check if we left the section (encountered another header)
        if (inSection && line.match(/^【.*】$/)) {
            inSection = false;
        }
        
        // If not in section, keep line
        if (!inSection) {
            filteredLines.push(line);
            return;
        }
        
        // In the section - filter content based on store type markers
        // Lines with 🏭 are self-operation, 🔗 are franchise
        var isSelfOp = line.includes('🏭自营') || line.includes('🏭');
        var isFranchise = line.includes('🔗加盟') || line.includes('🔗');
        
        // Check if this is a total/summary line (contains "总计" or "总" or ends with "合计")
        var isTotal = line.match(/^[-\s]*(总计|总计)/) || line.includes('├─') || line.includes('└─') || line.includes('合计');
        
        // For sections that mix self-op and franchise, filter based on type
        // Keep totals always, filter individual stores
        if (isTotal) {
            // For totals, we need to split and filter
            if (showAll) {
                filteredLines.push(line);
            } else if (filterType === '自营') {
                // Only keep lines with self-op data
                if (isSelfOp || line.match(/^[-\s]*🏭/)) {
                    filteredLines.push(line);
                } else if (line.match(/^[-\s]*🔗/)) {
                    // Skip franchise totals when filtering self-op
                } else {
                    filteredLines.push(line);
                }
            } else if (filterType === '加盟') {
                // Only keep lines with franchise data
                if (isFranchise || line.match(/^[-\s]*🔗/)) {
                    filteredLines.push(line);
                } else if (line.match(/^[-\s]*🏭/)) {
                    // Skip self-op totals when filtering franchise
                }
            }
            return;
        }
        
        // For non-total lines, filter by store type
        if (showAll) {
            filteredLines.push(line);
        } else if (filterType === '自营') {
            if (isSelfOp || !isFranchise) {
                filteredLines.push(line);
            }
        } else if (filterType === '加盟') {
            if (isFranchise) {
                filteredLines.push(line);
            }
        }
    });
    
    // Rebuild: header + filtered content
    if (headerEl) {
        var headerHtml = headerEl.outerHTML;
        contentEl.innerHTML = headerHtml + filteredLines.join('\n');
    } else {
        contentEl.innerHTML = filteredLines.join('\n');
    }
}
